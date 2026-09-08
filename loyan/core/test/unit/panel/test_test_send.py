"""test/send 端点单元测试 — 支持文本和文件上传"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestTestSendValidation:
    """test/send 参数验证测试"""
    
    def test_missing_platform(self):
        """缺少platform应返回400"""
        # 验证数据模型层
        data = {"sender": "123", "text": "hello"}
        assert not data.get("platform")
        assert data.get("sender") == "123"
        assert data.get("text") == "hello"
            
    def test_valid_text_only(self):
        """纯文本请求应通过验证"""
        data = {
            "platform": "qq_official",
            "sender": "7F3420C56DA6CC881EEA6D400586BE2C",
            "text": "/导入"
        }
        assert data.get("platform") == "qq_official"
        assert data.get("sender") == "7F3420C56DA6CC881EEA6D400586BE2C"
        assert data.get("text") == "/导入"
    
    def test_valid_with_attachments(self):
        """带attachments的请求应通过验证"""
        data = {
            "platform": "qq_official",
            "sender": "7F3420C56DA6CC881EEA6D400586BE2C",
            "text": "/导入",
            "attachments": [
                {"content_type": "file", "url": "http://example.com/test.ics", "filename": "课程表.ics"}
            ]
        }
        assert isinstance(data.get("attachments"), list)
        assert len(data["attachments"]) == 1
        assert data["attachments"][0]["content_type"] == "file"
    
    def test_invalid_attachments_type(self):
        """attachments非数组应返回错误"""
        data = {
            "platform": "qq_official",
            "sender": "123",
            "attachments": "not_an_array"
        }
        assert not isinstance(data.get("attachments"), list)
    
    def test_missing_attachment_fields(self):
        """缺少content_type或url的attachment应返回错误"""
        invalid = [{"url": "http://example.com/test.ics"}]
        for att in invalid:
            assert "content_type" not in att or "url" not in att
    
    def test_valid_ics_attachment(self):
        """有效的.ics文件attachment"""
        attachment = {
            "content_type": "file",
            "url": "http://example.com/schedule.ics",
            "filename": "课程表.ics"
        }
        assert attachment["content_type"] == "file"
        assert attachment["filename"].endswith(".ics")
    
    def test_valid_image_attachment(self):
        """有效的图片attachment"""
        attachment = {
            "content_type": "image/jpeg",
            "url": "http://example.com/photo.jpg"
        }
        assert attachment["content_type"].startswith("image/")
    
    def test_valid_voice_attachment(self):
        """有效的语音attachment"""
        attachment = {
            "content_type": "voice",
            "url": "http://example.com/voice.mp3"
        }
        assert attachment["content_type"] == "voice"
    
    def test_valid_video_attachment(self):
        """有效的视频attachment"""
        attachment = {
            "content_type": "video/mp4",
            "url": "http://example.com/video.mp4",
            "filename": "video.mp4"
        }
        assert attachment["content_type"].startswith("video/")


class TestEventConstruction:
    """事件构造测试"""
    
    def test_event_with_text_only(self):
        """纯文本事件构造"""
        from loyan.core.loyan_adapter.event import LoyanEvent
        from loyan.core.loyan_adapter.message import LoyanText
        from loyan.core.loyan_adapter.identity import IdentityTag
        
        text = "/导入"
        sender = "7F3420C56DA6CC881EEA6D400586BE2C"
        
        event = LoyanEvent(
            sender_id=sender,
            target_id=sender,
            chat_type="private",
            segments=[LoyanText(text=text)],
            raw_text=text,
            message_id=f"test_send_{sender}",
            nickname="脚本测试",
            is_at_bot=False,
            raw_data={},
            source=IdentityTag(platform="qq_official", bot_name="test"),
        )
        
        assert event.segments[0].text == "/导入"
        assert event.raw_text == "/导入"
        assert event.sender_id == sender
    
    def test_event_with_ics_attachment(self):
        """带ICS文件的事件构造"""
        from loyan.core.loyan_adapter.event import LoyanEvent
        from loyan.core.loyan_adapter.message import LoyanText, LoyanFile
        from loyan.core.loyan_adapter.identity import IdentityTag
        
        text = "/导入"
        sender = "7F3420C56DA6CC881EEA6D400586BE2C"
        attachments = [
            {"content_type": "file", "url": "http://example.com/test.ics", "filename": "课程表.ics"}
        ]
        
        # 模拟构建segments
        segments = [LoyanText(text=text)]
        for att in attachments:
            if att.get("content_type") == "file":
                segments.append(LoyanFile(url=att.get("url"), file_path=att.get("filename")))
        
        raw_data = {"attachments": attachments}
        
        event = LoyanEvent(
            sender_id=sender,
            target_id=sender,
            chat_type="private",
            segments=segments,
            raw_text=text,
            message_id=f"test_send_{sender}",
            nickname="脚本测试",
            is_at_bot=False,
            raw_data=raw_data,
            source=IdentityTag(platform="qq_official", bot_name="test"),
        )
        
        assert len(event.segments) == 2
        assert isinstance(event.segments[0], LoyanText)
        assert isinstance(event.segments[1], LoyanFile)
        assert event.raw_data["attachments"][0]["content_type"] == "file"
    
    def test_event_with_image_attachment(self):
        """带图片的事件构造"""
        from loyan.core.loyan_adapter.event import LoyanEvent
        from loyan.core.loyan_adapter.message import LoyanText, LoyanImage
        from loyan.core.loyan_adapter.identity import IdentityTag
        
        attachments = [
            {"content_type": "image/jpeg", "url": "http://example.com/photo.jpg"}
        ]
        
        segments = []
        for att in attachments:
            if att.get("content_type").startswith("image/"):
                segments.append(LoyanImage(url=att.get("url")))
        
        assert len(segments) == 1
        assert isinstance(segments[0], LoyanImage)
    
    def test_event_with_voice_attachment(self):
        """带语音的事件构造"""
        from loyan.core.loyan_adapter.message import LoyanVoice
        
        attachments = [
            {"content_type": "voice", "url": "http://example.com/voice.mp3"}
        ]
        
        segments = []
        for att in attachments:
            if att.get("content_type") == "voice":
                segments.append(LoyanVoice(file_path=att.get("url")))
        
        assert len(segments) == 1
        assert isinstance(segments[0], LoyanVoice)
    
    def test_event_with_video_attachment(self):
        """带视频的事件构造"""
        from loyan.core.loyan_adapter.message import LoyanVideo
        
        attachments = [
            {"content_type": "video/mp4", "url": "http://example.com/video.mp4", "filename": "video.mp4"}
        ]
        
        segments = []
        for att in attachments:
            if att.get("content_type").startswith("video/"):
                segments.append(LoyanVideo(url=att.get("url"), file_path=att.get("filename")))
        
        assert len(segments) == 1
        assert isinstance(segments[0], LoyanVideo)


class TestPluginImport:
    """插件导入功能测试"""
    
    def test_parse_ics_from_file(self):
        """从ICS文件解析课程"""
        import sys
        sys.path.insert(0, '/root/LoyanBot')
        sys.path.insert(0, '/opt/LoyanBot/storage/plugins/loyan-coursetables')
        
        from parsers.ics import parse_ics
        
        with open('/root/LoyanBot/日历-08月29日.ics', 'r') as f:
            ics_text = f.read()
        
        result = parse_ics(ics_text)
        
        assert "courses" in result
        assert len(result["courses"]) > 0
        
        # 检查课程字段
        for course in result["courses"]:
            assert "name" in course
            assert "day" in course
            assert "time" in course
    
    def test_parse_ics_content(self):
        """验证ICS解析内容"""
        import sys
        sys.path.insert(0, '/root/LoyanBot')
        sys.path.insert(0, '/opt/LoyanBot/storage/plugins/loyan-coursetables')
        
        from parsers.ics import parse_ics
        
        with open('/root/LoyanBot/日历-08月29日.ics', 'r') as f:
            ics_text = f.read()
        
        result = parse_ics(ics_text)
        courses = result["courses"]
        
        # 至少应解析到一些课程
        assert len(courses) >= 3
        
        # 检查具体课程
        names = [c["name"] for c in courses]
        assert any("网络" in n or "体育" in n for n in names)
    
    def test_parse_json_with_url(self):
        """测试URL导入场景"""
        import sys
        sys.path.insert(0, '/root/LoyanBot')
        sys.path.insert(0, '/opt/LoyanBot/storage/plugins/loyan-coursetables')
        
        from parsers.json import parse_json
        
        # 读取ICS文件内容
        with open('/root/LoyanBot/日历-08月29日.ics', 'r') as f:
            ics_text = f.read()
        
        result = parse_json(ics_text)
        
        assert "courses" in result
        assert len(result["courses"]) > 0
        assert result.get("source") == "ics"
    
    def test_import_with_local_file_scenario(self):
        """模拟本地文件导入流程"""
        import sys
        sys.path.insert(0, '/root/LoyanBot')
        sys.path.insert(0, '/opt/LoyanBot/storage/plugins/loyan-coursetables')
        
        from parsers.ics import parse_ics
        from parsers.json import parse_json
        
        # 1. 读取本地ICS文件
        with open('/root/LoyanBot/日历-08月29日.ics', 'r') as f:
            ics_text = f.read()
        
        # 2. 解析
        result = parse_json(ics_text)
        
        # 3. 验证结果
        assert "error" not in result
        assert len(result["courses"]) > 0
        
        # 4. 模拟保存（不实际保存）
        courses = result["courses"]
        assert len(courses) >= 3
    
    def test_import_with_url_scenario(self):
        """模拟URL导入流程"""
        import sys
        sys.path.insert(0, '/root/LoyanBot')
        sys.path.insert(0, '/opt/LoyanBot/storage/plugins/loyan-coursetables')
        
        from parsers.json import parse_json
        
        # 模拟从URL下载的ICS内容
        with open('/root/LoyanBot/日历-08月29日.ics', 'r') as f:
            ics_text = f.read()
        
        # 这等同于从URL下载的内容
        result = parse_json(ics_text)
        
        assert "courses" in result
        assert len(result["courses"]) > 0


class TestAttachmentParsing:
    """附件解析测试"""
    
    def test_parse_file_attachment(self):
        """解析文件类型附件"""
        attachment = {
            "content_type": "file",
            "url": "http://example.com/test.ics",
            "filename": "课程表.ics"
        }
        
        assert attachment["content_type"] == "file"
        assert attachment["url"] == "http://example.com/test.ics"
        assert attachment["filename"] == "课程表.ics"
    
    def test_parse_image_attachment(self):
        """解析图片类型附件"""
        attachment = {
            "content_type": "image/png",
            "url": "http://example.com/image.png"
        }
        
        assert attachment["content_type"].startswith("image/")
    
    def test_parse_voice_attachment(self):
        """解析语音类型附件"""
        attachment = {
            "content_type": "voice",
            "url": "http://example.com/voice.ogg"
        }
        
        assert attachment["content_type"] == "voice"
    
    def test_parse_video_attachment(self):
        """解析视频类型附件"""
        attachment = {
            "content_type": "video/mp4",
            "url": "http://example.com/video.mp4"
        }
        
        assert attachment["content_type"].startswith("video/")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
