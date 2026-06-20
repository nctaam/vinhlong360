"""Tests for social.py Pydantic models and validation logic (no DB required)."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")

from social import CreatePost, CreateComment, POST_TYPES, POST_TYPE_LABELS


class TestCreatePostModel:
    def test_valid_share(self):
        p = CreatePost(content="Chia sẻ trải nghiệm du lịch Vĩnh Long rất đẹp", post_type="share")
        assert p.post_type == "share"
        assert len(p.content) >= 10

    def test_valid_review_with_rating(self):
        p = CreatePost(content="Cam sành rất ngon, ngọt thanh", post_type="review", rating=5, entity_id="cam-sanh")
        assert p.rating == 5
        assert p.entity_id == "cam-sanh"

    def test_content_too_short(self):
        with pytest.raises(ValueError, match="10 ký tự"):
            CreatePost(content="ngắn", post_type="share")

    def test_content_too_long(self):
        with pytest.raises(ValueError, match="5000 ký tự"):
            CreatePost(content="x" * 5001, post_type="share")

    def test_invalid_post_type(self):
        with pytest.raises(ValueError, match="Loại bài viết"):
            CreatePost(content="Nội dung hợp lệ đủ dài", post_type="invalid")

    def test_rating_out_of_range(self):
        with pytest.raises(ValueError, match="1 đến 5"):
            CreatePost(content="Đánh giá ngoài phạm vi cho phép", post_type="review", rating=6)

    def test_rating_zero(self):
        with pytest.raises(ValueError, match="1 đến 5"):
            CreatePost(content="Đánh giá ngoài phạm vi cho phép", post_type="review", rating=0)

    def test_all_post_types_valid(self):
        for pt in POST_TYPES:
            p = CreatePost(content=f"Nội dung hợp lệ cho loại {pt}", post_type=pt)
            assert p.post_type == pt

    def test_post_type_labels_cover_all_types(self):
        for pt in POST_TYPES:
            assert pt in POST_TYPE_LABELS


class TestCreateCommentModel:
    def test_valid_comment(self):
        c = CreateComment(content="Bình luận hay!")
        assert c.content == "Bình luận hay!"

    def test_empty_comment(self):
        with pytest.raises(ValueError, match="không được để trống"):
            CreateComment(content="")

    def test_comment_too_long(self):
        with pytest.raises(ValueError, match="2000 ký tự"):
            CreateComment(content="x" * 2001)

    def test_comment_with_parent(self):
        c = CreateComment(content="Reply", parent_id="comment-123")
        assert c.parent_id == "comment-123"

    def test_content_stripped(self):
        c = CreateComment(content="  trimmed  ")
        assert c.content == "trimmed"
