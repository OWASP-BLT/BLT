ISSUE_COMMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["created", "edited", "deleted"]},
        "comment": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "minLength": 1},
                "user": {"type": "object", "properties": {"login": {"type": "string"}}, "required": ["login", "type"]},
            },
            "required": ["body", "user"],
        },
        "issue": {"type": "object", "properties": {"pull_request": {"type": "object"}}},
    },
    "required": ["action", "issue", "comment"],
}


INSTALLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["created", "deleted", "suspend", "unsuspend"]},
        "installation": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "app_id": {"type": "integer"},
                "app_slug": {"type": "string"},
                "account": {
                    "type": "object",
                    "properties": {"login": {"type": "string"}, "type": {"type": "string"}},
                    "required": ["login", "type"],
                },
                "permissions": {"type": "object", "additionalProperties": {"type": "string"}},
                "events": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["id", "app_id", "app_slug", "account"],
        },
        "repositories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "full_name": {"type": "string"},
                    "private": {"type": "boolean"},
                },
                "required": ["id", "name", "full_name", "private"],
            },
        },
        "sender": {"type": "object", "properties": {"login": {"type": "string"}}, "required": ["login"]},
    },
    "required": ["action", "installation", "sender"],
}

INSTALLATION_REPOSITORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "installation": {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "app_slug": {"type": "string"}},
            "required": ["id", "app_slug"],
        },
        "sender": {"type": "object", "properties": {"login": {"type": "string"}}, "required": ["login"]},
        "repositories_added": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "full_name": {"type": "string"},
                    "private": {"type": "boolean"},
                },
                "required": ["id", "name", "full_name", "private"],
            },
            "default": [],
        },
        "repositories_removed": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "full_name": {"type": "string"},
                    "private": {"type": "boolean"},
                },
                "required": ["id", "name", "full_name", "private"],
            },
            "default": [],
        },
    },
    "required": ["installation", "sender", "repositories_added", "repositories_removed"],
}


ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["opened", "edited"]},
        "issue": {
            "type": "object",
            "properties": {
                "number": {"type": "integer", "minimum": 1},
                "title": {"type": "string", "minLength": 1},
                "body": {"type": ["string", "null"], "default": "null"},
                "user": {
                    "type": "object",
                    "properties": {"login": {"type": "string"}, "type": {"type": "string", "enum": ["User"]}},
                    "required": ["login", "type"],
                },
            },
            "required": ["number", "title", "user"],
        },
        "changes": {
            "type": "object",
            "properties": {
                "title": {"type": "object", "properties": {"from": {"type": "string"}}, "required": ["from"]},
                "body": {"type": "object", "properties": {"from": {"type": "string"}}, "required": ["from"]},
            },
        },
    },
    "required": ["action", "issue"],
}


PR_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["opened", "synchronize", "closed", "reopened"]},
        "pull_request": {
            "type": "object",
            "properties": {
                "number": {"type": "integer", "minimum": 1},
                "title": {"type": "string", "minLength": 1},
                "body": {"type": ["string", "null"], "default": "null"},
                "commits": {"type": "integer", "minimum": 1},
                "changed_files": {"type": "integer", "minimum": 1},
                "diff_url": {"type": "string", "format": "uri"},
                "patch_url": {"type": "string", "format": "uri"},
                "user": {
                    "type": "object",
                    "properties": {"login": {"type": "string"}, "type": {"type": "string"}},
                    "required": ["login", "type"],
                },
            },
            "required": ["number", "title", "commits", "changed_files", "diff_url", "patch_url", "user"],
        },
    },
    "required": ["action", "pull_request"],
}


PUSH_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "installation": {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "app_slug": {"type": "string"}},
            "required": ["id", "app_slug"],
        },
        "repository": {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "full_name": {"type": "string"}, "private": {"type": "boolean"}},
            "required": ["id", "full_name"],
        },
        "before": {"type": "string", "description": "Commit SHA before the push"},
        "after": {"type": "string", "description": "Commit SHA after the push"},
        "sender": {"type": "object", "properties": {"login": {"type": "string"}}, "required": ["login"]},
    },
    "required": ["installation", "repository", "before", "after", "sender"],
}


REPOSITORY_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "created",
                "deleted",
                "archived",
                "unarchived",
                "renamed",
                "transferred",
                "publicized",
                "privatized",
            ],
        },
        "installation": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
        "repository": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "full_name": {"type": "string"},
                "private": {"type": "boolean"},
            },
            "required": ["id", "full_name"],
        },
        "sender": {"type": "object", "properties": {"login": {"type": "string"}}, "required": ["login"]},
    },
    "required": ["action", "installation", "repository", "sender"],
}
