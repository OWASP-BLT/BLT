CONTEXT:
Code chunks are embedded using gemini models/text-embedding-004

Chunks represent semantic units: functions, classes, methods, config blocks, etc.

Embeddings capture both syntactic and semantic similarity

Retrieved chunks provide context for downstream PR analysis (bug detection, test suggestions, consistency checks)

TASK:
Generate a search query that retrieves the most relevant code chunks for a given pull request (PR) diff. Focus on:

* **Core functionality** being modified or added
* **Related components** that might be affected across the codebase
* **Similar patterns or structures** elsewhere (e.g., reusable utility functions, base classes)

Structure your output as follows:

[QUERY]: <natural language summary of the functionality>
[KEY TERMS]: <key technical concepts, identifiers, function names, modules, and semantically related terms>
[K]: <recommended value, between 3 and 10>
[REASONING]: <brief, concise explanation of what the change does and why these related chunks would help.>

Tips:
* [QUERY] should describe the intent of the change using natural language.
* [KEY TERMS] act as semantic anchors: function names, config keys, domain terms.
* If diff contains function/class/middleware definitions, abstract them (e.g., “validate auth token using JWT”).

K-SELECTION RULES:
| Change Type                 | Recommended K | Notes                                 |
| :-------------------------- | :------------ | :------------------------------------ |
| Small, focused changes (1 file) | 3–5         | New logic, refactors, bugfixes        |
| Medium changes (2–5 files)  | 5–7         | Touches multiple layers               |
| Large/widespread changes (>5 files)| 7–10        | Affects shared components             |
| Involving base class/middleware | 7–10        | High risk of ripple effects           |
| Introducing new module      | 3–5         | Localized need for context            |

Special Considerations:
* **Highly Abstract Changes:** For changes that are very abstract (e.g., modifying an interface definition without concrete implementations), focus on the implications for consumers of that interface.
* **Trivial Changes with Broad Impact:** If a seemingly small change (e.g., a constant value) could have widespread implications, consider a higher `K` and broader `KEY TERMS` that reflect its usage.
* **Non-Code Changes (e.g., Configuration):** For configuration-only changes, identify the systems or modules that consume that configuration.

EXAMPLES:
1. Middleware Auth Addition
[QUERY]: add authentication enforcement middleware for protecting routes and managing user sessions
[KEY TERMS]: auth_middleware, request.user, authentication, token, session
[K]: 5
[REASONING]: This change introduces auth middleware logic, so related user session handling, token parsing, and protected route enforcement chunks are useful for context.

2. Database Refactor
[QUERY]: refactor database connection pooling logic to improve performance and thread safety
[KEY TERMS]: init_db_pool, db_connection, connection pooling, cleanup, thread-safe
[K]: 8
[REASONING]: The update restructures how DB connections are managed, so relevant initialization and teardown logic, as well as threading-safe utilities, should be retrieved.

3. Utility Function Bug Fix
[QUERY]: fix off-by-one error in pagination utility function calculation
[KEY TERMS]: paginate, page_size, total_items, offset, utility
[K]: 3
[REASONING]: This fix corrects a specific calculation within a utility. Retrieving similar utility functions or other pagination logic will help ensure consistency and prevent regressions.
