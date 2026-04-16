from __future__ import annotations

from flask import session

from ..models import User


def _selected_child_key(family_id: int) -> str:
    return f"selected_child_{family_id}"


def get_family_children(family_id: int) -> list[User]:
    return (
        User.query.filter_by(family_id=family_id, role="child")
        .order_by(User.created_at.asc(), User.id.asc())
        .all()
    )


def get_selected_child(family_id: int) -> tuple[User | None, list[User]]:
    children = get_family_children(family_id)
    if not children:
        return None, []

    selected_id = session.get(_selected_child_key(family_id))
    selected_child = next((child for child in children if child.id == selected_id), None)
    if selected_child is None:
        selected_child = children[0]
        session[_selected_child_key(family_id)] = selected_child.id
    return selected_child, children


def set_selected_child(family_id: int, child_id: int) -> User | None:
    selected_child = (
        User.query.filter_by(id=child_id, family_id=family_id, role="child").first()
    )
    if selected_child is None:
        return None
    session[_selected_child_key(family_id)] = selected_child.id
    return selected_child
