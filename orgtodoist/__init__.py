from typing import List, Union, Optional, Any, Dict, TypedDict, Final
from dataclasses import dataclass
from datetime import datetime
import os
import sys
import re
import todoist  # type: ignore
from xdg import XDG_CONFIG_HOME  # type: ignore

MARKDOWN_LINK_REGEX: Final = re.compile(r"\[([^]]+)\]\(([^)]+)\)")


def get_todoist_token() -> Optional[str]:
    config_file = XDG_CONFIG_HOME / "org-todoist" / "token.txt"

    if config_file.exists():
        with config_file.open() as f:
            token_unstripped: str = f.readline()
            return token_unstripped.strip()

    if "TODOIST_TOKEN" not in os.environ:
        sys.stderr.write(
            "We need a valid todoist token inside the TODOIST_TOKEN environment variable\n"
        )
        sys.stderr.write(
            "See the manual: https://developer.todoist.com/sync/v8/?shell#authorization\n\n"
        )
        sys.stderr.write(
            "Alternatively, provide a configuration file at " + config_file
        )
        return None

    return os.environ["TODOIST_TOKEN"]


@dataclass(frozen=True)
class OrgHeadline:
    title: str
    todo_state: Optional[str]
    scheduling: Optional[datetime]
    sub_headlines: List["OrgHeadline"]


OrgDocument = List[OrgHeadline]


class TodoistDue(TypedDict):
    date: str
    timezone: Optional[str]
    string: str
    lang: str
    is_recurring: bool


class TodoistItem(TypedDict):
    id: int
    project_id: int
    content: str
    due: Optional[TodoistDue]
    parent_id: Optional[int]
    in_history: int
    is_deleted: int


class TodoistProject(TypedDict):
    id: int
    parent_id: Optional[int]
    name: str


class TodoistState(TypedDict):
    projects: List[TodoistProject]
    items: List[TodoistItem]


@dataclass(frozen=True)
class TodoistTreeItem:
    state: TodoistItem
    sub_item: List["TodoistTreeItem"]


@dataclass(frozen=True)
class TodoistTreeProject:
    state: TodoistProject
    items: List[TodoistTreeItem]


TodoistTree = List[TodoistTreeProject]


def build_todoist_tree(state: TodoistState) -> TodoistTree:
    def build_todoist_item_tree(
        items: List[TodoistItem], parent_item: TodoistItem
    ) -> TodoistTreeItem:
        return TodoistTreeItem(
            parent_item,
            [
                build_todoist_item_tree(items, sub_item)
                for sub_item in items
                if sub_item["parent_id"] == parent_item["id"]
            ],
        )

    def build_todoist_project_tree(
        state: TodoistState, project: TodoistProject
    ) -> TodoistTreeProject:
        return TodoistTreeProject(
            project,
            [
                build_todoist_item_tree(state["items"], item)
                for item in state["items"]
                if item["project_id"] == project["id"]
                and item["parent_id"] is None
                and item["is_deleted"] != 1
                and item["in_history"] != 1
            ],
        )

    return [build_todoist_project_tree(state, p) for p in state["projects"]]


def serialize_todoist_tree(t: TodoistTree) -> None:
    for p in t:
        for i in p.items:
            print("  " + i.state["content"])


def convert_to_org(t: TodoistTree) -> OrgDocument:
    def due_to_org(d: TodoistDue) -> datetime:
        date = d["date"]
        return datetime.fromisoformat(date)

    def item_to_org_headline(t: TodoistTreeItem) -> OrgHeadline:
        return OrgHeadline(
            title=t.state["content"],
            todo_state="TODO",
            scheduling=due_to_org(t.state["due"])
            if t.state["due"] is not None
            else None,
            sub_headlines=[item_to_org_headline(ts) for ts in t.sub_item],
        )

    def project_to_org_headline(t: TodoistTreeProject) -> OrgHeadline:
        return OrgHeadline(
            title=t.state["name"],
            todo_state=None,
            scheduling=None,
            sub_headlines=[item_to_org_headline(ti) for ti in t.items],
        )

    return [project_to_org_headline(p) for p in t]


def serialize_org(t: OrgDocument) -> None:
    def convert_org_title(t: str) -> str:
        return MARKDOWN_LINK_REGEX.sub(r"[[\2][\1]]", t)

    def serialize_org_headline(depth: int, o: OrgHeadline) -> None:
        print(
            (depth * "*")
            + " "
            + (o.todo_state + " " if o.todo_state is not None else "")
            + convert_org_title(o.title)
        )
        if o.scheduling is not None:
            if o.scheduling.hour != 0 or o.scheduling.minute != 0:
                print("SCHEDULED: <" + o.scheduling.strftime("%Y-%m-%d %H:%M") + ">")
            else:
                print(f"SCHEDULED: <{o.scheduling.strftime('%Y-%m-%d')}>")
        for sh in o.sub_headlines:
            serialize_org_headline(depth + 1, sh)

    for p in t:
        serialize_org_headline(1, p)


def main_inner() -> int:
    api = todoist.TodoistAPI(get_todoist_token())
    api.sync()

    serialize_org(convert_to_org(build_todoist_tree(api.state)))

    return 0


def main() -> None:
    exit_code = main_inner()

    if exit_code != 0:
        sys.exit(exit_code)
