"""ELK查询客户端 - 通过HTTP API直接访问ES"""
import requests
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path


class ELKClient:
    """ES HTTP API客户端"""

    def __init__(
        self,
        es_host: Optional[str] = None,
        index_pattern: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """初始化ELK客户端

        Args:
            es_host: ES地址，默认从配置文件读取
            index_pattern: 索引模式，默认logstash-*
            config_path: 配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "elk_config.yaml"

        self._load_config(config_path)

        if es_host:
            self.es_host = es_host
        if index_pattern:
            self.index_pattern = index_pattern

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        if self.auth_enabled:
            self.session.auth = (self.auth_username, self.auth_password)

    def _load_config(self, config_path: Path):
        """加载配置文件"""
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                elk = config.get("elk", {})

                self.es_host = elk.get("es_host", "http://192.168.100.219:9200")
                self.index_pattern = elk.get("index", {}).get("pattern", "logstash-*")
                self.time_field = elk.get("index", {}).get("time_field", "@timestamp")

                auth = elk.get("auth", {})
                self.auth_enabled = auth.get("enabled", False)
                self.auth_username = auth.get("username", "")
                self.auth_password = auth.get("password", "")

                query = elk.get("query", {})
                self.default_time_range = query.get("default_time_range_hours", 24)
                self.max_size = query.get("max_size", 10000)
                self.timeout = query.get("timeout_seconds", 60)
        else:
            # 默认配置
            self.es_host = "http://192.168.100.219:9200"
            self.index_pattern = "logstash-*"
            self.time_field = "@timestamp"
            self.auth_enabled = False
            self.default_time_range = 24
            self.max_size = 10000
            self.timeout = 60

    def search(
        self,
        query: Dict[str, Any],
        index: Optional[str] = None,
        time_range_hours: Optional[int] = None,
        size: Optional[int] = None,
        sort_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行搜索

        Args:
            query: ES查询DSL
            index: 索引模式，默认使用配置的index_pattern
            time_range_hours: 时间范围（小时），默认24
            size: 返回条数，默认100
            sort_field: 排序字段，默认@timestamp

        Returns:
            ES搜索结果
        """
        if index is None:
            index = self.index_pattern
        if time_range_hours is None:
            time_range_hours = self.default_time_range
        if size is None:
            size = 100
        if sort_field is None:
            sort_field = self.time_field

        # 构建完整查询DSL
        dsl = self._build_dsl(query, time_range_hours, size, sort_field)

        url = f"{self.es_host}/{index}/_search"
        resp = self.session.post(url, json=dsl, timeout=self.timeout)
        resp.raise_for_status()

        return resp.json()

    def _build_dsl(
        self,
        query: Dict[str, Any],
        time_range_hours: int,
        size: int,
        sort_field: str
    ) -> Dict[str, Any]:
        """构建完整查询DSL"""
        # 如果query已经是bool查询，添加时间过滤
        if "bool" in query:
            dsl = {
                "query": query,
                "size": min(size, self.max_size),
                "sort": [{sort_field: {"order": "desc"}}]
            }
            # 添加时间过滤到filter
            if "filter" not in dsl["query"]["bool"]:
                dsl["query"]["bool"]["filter"] = []
            dsl["query"]["bool"]["filter"].append({
                "range": {self.time_field: {"gte": f"now-{time_range_hours}h"}}
            })
        else:
            # 包装成bool查询
            dsl = {
                "query": {
                    "bool": {
                        "must": [query] if query != {"match_all": {}} else [],
                        "filter": [{
                            "range": {self.time_field: {"gte": f"now-{time_range_hours}h"}}
                        }]
                    }
                },
                "size": min(size, self.max_size),
                "sort": [{sort_field: {"order": "desc"}}]
            }
            if query == {"match_all": {}}:
                dsl["query"]["bool"]["must"] = [{"match_all": {}}]

        return dsl

    def search_exceptions(
        self,
        keywords: List[str],
        time_range_hours: int = 1,
        size: int = 100
    ) -> Dict[str, Any]:
        """搜索异常日志

        Args:
            keywords: 关键字列表
            time_range_hours: 时间范围
            size: 返回条数

        Returns:
            包含total和logs的简化结果
        """
        # 构建关键字匹配查询
        should = [{"match_phrase": {"message": kw}} for kw in keywords]
        query = {
            "bool": {
                "should": should,
                "minimum_should_match": 1
            }
        }

        result = self.search(query, time_range_hours=time_range_hours, size=size)

        # 简化结果
        hits = result.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        logs = [
            {
                "timestamp": hit["_source"].get(self.time_field),
                "message": hit["_source"].get("message"),
                "level": hit["_source"].get("level"),
                "app_name": hit["_source"].get("app_name")
            }
            for hit in hits.get("hits", [])
        ]

        return {"total": total, "logs": logs}

    def aggregate(
        self,
        agg_name: str,
        field: str,
        query: Optional[Dict[str, Any]] = None,
        size: int = 20,
        time_range_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行聚合查询

        Args:
            agg_name: 聚合名称
            field: 聚合字段
            query: 过滤查询
            size: 聚合桶数量
            time_range_hours: 时间范围

        Returns:
            聚合结果
        """
        if query is None:
            query = {"match_all": {}}
        if time_range_hours is None:
            time_range_hours = self.default_time_range

        dsl = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [query] if query != {"match_all": {}} else [],
                    "filter": [{
                        "range": {self.time_field: {"gte": f"now-{time_range_hours}h"}}
                    }]
                }
            },
            "aggs": {
                agg_name: {
                    "terms": {"field": field, "size": size}
                }
            }
        }

        url = f"{self.es_host}/{self.index_pattern}/_search"
        resp = self.session.post(url, json=dsl, timeout=self.timeout)
        resp.raise_for_status()

        return resp.json()

    def get_indices(self, pattern: Optional[str] = None) -> List[str]:
        """获取索引列表

        Args:
            pattern: 索引模式，默认使用配置的index_pattern

        Returns:
            索引名称列表
        """
        if pattern is None:
            pattern = self.index_pattern

        url = f"{self.es_host}/_cat/indices/{pattern}?format=json"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

        return [idx["index"] for idx in resp.json()]

    def health_check(self) -> bool:
        """健康检查"""
        try:
            url = f"{self.es_host}/_cluster/health"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json().get("status") in ["green", "yellow"]
        except Exception:
            return False