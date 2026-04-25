"""ELK查询客户端测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.elk_client import ELKClient


class TestELKClient:
    """ELKClient测试类"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        client = ELKClient()
        assert client.es_host == "http://192.168.100.219:9200"
        assert client.index_pattern == "logstash-*"

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        client = ELKClient(
            es_host="http://custom:9200",
            index_pattern="app-*"
        )
        assert client.es_host == "http://custom:9200"
        assert client.index_pattern == "app-*"

    @patch('core.elk_client.requests.Session')
    def test_search_basic(self, mock_session_class):
        """测试基本搜索"""
        mock_session = MagicMock()
        mock_response = Mock(
            status_code=200,
            json=lambda: {"hits": {"hits": [{"_source": {"message": "test"}}]}}
        )
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = ELKClient()
        result = client.search({"query": {"match_all": {}}})

        assert "hits" in result
        mock_session.post.assert_called_once()

    @patch('core.elk_client.requests.Session')
    def test_search_with_time_range(self, mock_session_class):
        """测试带时间范围的搜索"""
        mock_session = MagicMock()
        mock_response = Mock(
            status_code=200,
            json=lambda: {"hits": {"hits": []}}
        )
        mock_session.post.return_value = mock_response
        mock_session.headers.update = MagicMock()
        mock_session_class.return_value = mock_session

        client = ELKClient()
        result = client.search(
            query={"match": {"message": "ERROR"}},
            time_range_hours=24
        )

        assert result is not None
        call_args = mock_session.post.call_args
        body = call_args[1]["json"]
        assert "query" in body
        assert "bool" in body["query"]

    @patch('core.elk_client.requests.Session')
    def test_search_exception_logs(self, mock_session_class):
        """测试异常日志搜索"""
        mock_session = MagicMock()
        mock_response = Mock(
            status_code=200,
            json=lambda: {
                "hits": {
                    "total": {"value": 100},
                    "hits": [
                        {"_source": {"message": "ChannelTimeoutException", "@timestamp": "2026-04-25T10:00:00"}},
                        {"_source": {"message": "PaymentFailedException", "@timestamp": "2026-04-25T10:01:00"}}
                    ]
                }
            }
        )
        mock_session.post.return_value = mock_response
        mock_session.headers.update = MagicMock()
        mock_session_class.return_value = mock_session

        client = ELKClient()
        result = client.search_exceptions(
            keywords=["timeout", "超时"],
            time_range_hours=1
        )

        assert result["total"] == 100
        assert len(result["logs"]) == 2

    @patch('core.elk_client.requests.Session')
    def test_get_indices(self, mock_session_class):
        """测试获取索引列表"""
        mock_session = MagicMock()
        mock_response = Mock(
            status_code=200,
            json=lambda: [{"index": "logstash-2026.04.25"}, {"index": "logstash-2026.04.24"}]
        )
        mock_session.get.return_value = mock_response
        mock_session.headers.update = MagicMock()
        mock_session_class.return_value = mock_session

        client = ELKClient()
        indices = client.get_indices()

        assert len(indices) == 2
        assert "logstash-2026.04.25" in indices

    @patch('core.elk_client.requests.Session')
    def test_aggregate_by_field(self, mock_session_class):
        """测试字段聚合"""
        mock_session = MagicMock()
        mock_response = Mock(
            status_code=200,
            json=lambda: {
                "aggregations": {
                    "by_app": {
                        "buckets": [{"key": "payment-service", "doc_count": 50}]
                    }
                }
            }
        )
        mock_session.post.return_value = mock_response
        mock_session.headers.update = MagicMock()
        mock_session_class.return_value = mock_session

        client = ELKClient()
        result = client.aggregate(
            agg_name="by_app",
            field="app_name.keyword"
        )

        assert "aggregations" in result
        assert "by_app" in result["aggregations"]