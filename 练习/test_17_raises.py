"""17：pytest.raises —— 怎么测"就应该报错"的场景。"""
import pytest


def test_除以零应该抛异常():
    with pytest.raises(ZeroDivisionError):
        1 / 0


def test_取不存在的字段应该报KeyError():
    with pytest.raises(KeyError):
        {}["不存在的字段"]


def test_还能顺便检查异常内容():
    with pytest.raises(ValueError) as e:
        raise ValueError("用户名不能为空")
    assert "不能为空" in str(e.value)
