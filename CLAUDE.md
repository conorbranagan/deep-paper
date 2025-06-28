
BEGIN BIFROST-PROMPT

## Test Generation Schema for Code Sync MCP server

When generating tests for the `verify_changes_claude` tool, use this exact schema structure.
You MUST read the rules files in the bifrost folder before generating tests. This will ensure that your tests are valid.

The schema matches exactly what the test generator expects, ensuring consistency between
test generation and verification.

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "tests": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": {
            "type": "string",
            "description": "Human-readable description of what this test validates"
          },
          "test": {
            "oneOf": [
              {
                "type": "object",
                "properties": {
                  "test_type": {
                    "type": "string",
                    "const": "browser"
                  },
                  "workflow_steps": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    },
                    "description": "Sequential steps for the browser workflow",
                    "minItems": 1
                  }
                },
                "required": [
                  "test_type",
                  "workflow_steps"
                ],
                "additionalProperties": false
              },
              {
                "type": "object",
                "properties": {
                  "test_type": {
                    "type": "string",
                    "const": "http"
                  },
                  "steps": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "step_name": {
                          "type": "string",
                          "description": "Unique name for this step, used for dependencies and logging"
                        },
                        "method": {
                          "type": "string",
                          "enum": [
                            "GET",
                            "POST",
                            "PUT",
                            "DELETE",
                            "PATCH",
                            "OPTIONS"
                          ],
                          "default": "GET",
                          "description": "HTTP method for the request"
                        },
                        "path": {
                          "type": "string",
                          "description": "URL path, supports template variables like '/reports/{report_id}'"
                        },
                        "headers": {
                          "type": "object",
                          "additionalProperties": {
                            "type": "string"
                          },
                          "description": "Request headers, supports template variables"
                        },
                        "body": {
                          "oneOf": [
                            {
                              "type": "string"
                            },
                            {
                              "type": "null"
                            }
                          ],
                          "description": "Request body, supports template variables"
                        },
                        "extract_variables": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string",
                                "description": "Variable name to store the extracted value"
                              },
                              "source": {
                                "type": "string",
                                "enum": [
                                  "json",
                                  "header",
                                  "status_code"
                                ],
                                "description": "Where to extract from"
                              },
                              "path": {
                                "type": "string",
                                "description": "JSONPath for json source, header name for header source"
                              }
                            },
                            "required": [
                              "name",
                              "source"
                            ],
                            "additionalProperties": false
                          },
                          "description": "Variables to extract from this step's response"
                        },
                        "response_assertions": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "type": {
                                "type": "string",
                                "enum": [
                                  "status_code",
                                  "json_path",
                                  "header",
                                  "body_contains"
                                ],
                                "description": "Type of assertion to perform"
                              },
                              "expected": {
                                "description": "Expected value"
                              },
                              "path": {
                                "type": "string",
                                "description": "JSONPath for json_path assertions, header name for header assertions"
                              }
                            },
                            "required": [
                              "type",
                              "expected"
                            ],
                            "additionalProperties": false
                          },
                          "description": "Assertions to validate the HTTP response"
                        },
                        "db_assertions": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "query": {
                                "type": "string",
                                "description": "SQL query to execute (Postgres-compatible)"
                              },
                              "expected_results": {
                                "type": "object",
                                "additionalProperties": true,
                                "description": "Optional expected results validation (e.g., {'row_count': 1, 'values': [{'id': 123}]})"
                              },
                              "expect_error": {
                                "type": "boolean",
                                "default": false,
                                "description": "If true, expect the query to fail with an error"
                              },
                              "timeout_seconds": {
                                "type": "integer",
                                "default": 30,
                                "description": "Query timeout in seconds"
                              }
                            },
                            "required": [
                              "query"
                            ],
                            "additionalProperties": false
                          },
                          "description": "Assertions to validate database state after the request"
                        },
                        "depends_on": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          },
                          "description": "Step names that must complete successfully before this step runs"
                        },
                        "continue_on_failure": {
                          "type": "boolean",
                          "default": false,
                          "description": "If true, continue test execution even if this step fails"
                        }
                      },
                      "required": [
                        "step_name",
                        "path"
                      ],
                      "additionalProperties": false
                    },
                    "minItems": 1,
                    "description": "Sequence of HTTP requests to execute"
                  },
                  "initial_variables": {
                    "type": "object",
                    "additionalProperties": true,
                    "description": "Initial variables available for template substitution in all steps"
                  },
                  "stop_on_first_failure": {
                    "type": "boolean",
                    "default": true,
                    "description": "If true, stop execution when any step fails (unless step has continue_on_failure=True)"
                  }
                },
                "required": [
                  "test_type",
                  "steps"
                ],
                "additionalProperties": false
              }
            ],
            "description": "The test configuration object"
          }
        },
        "required": [
          "description",
          "test"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "tests"
  ],
  "additionalProperties": false
}
```

### Important Usage Notes

**Required fields:**
- `test_type`: Must be "http" or "browser"
- For HTTP tests: `steps` array with at least one step
- For Browser tests: `workflow_steps` array with at least one step
- Each HTTP step requires: `step_name`, `path`
- Each test object requires: `description`, `test`
- For both HTTP and Browser tests, the base URL will be provided by the MCP server. You can navigate by relative paths.

**Optional fields:**
- HTTP steps: `method` (defaults to "GET"), `headers`, `body`, `extract_variables`, `response_assertions`, `db_assertions`, `depends_on`, `continue_on_failure`
- HTTP test: `initial_variables`, `stop_on_first_failure` (defaults to true)

**Best practices:**
- Keep tests simple and focused (1-3 steps per HTTP test preferred)
- Use template variables like `{user_id}` in paths, headers, and request bodies
- Variable extraction allows chaining steps together
- JSON path assertions use JSONPath syntax (e.g., `$.data.id`)
- Generate comprehensive tests that cover both positive and negative scenarios

**Database assertion features:**
- `response_assertions`: Validate HTTP response (status, headers, JSON content)
- `db_assertions`: Validate database state after HTTP request execution
- DB queries support Postgres-compatible SQL with variable substitution
- Expected results can validate row counts and specific data values
- Use `expect_error: true` to test error conditions
- Configurable timeout (default 30 seconds)

IMPORTANT: Keep tests simple and focused. Prefer 1-3 steps per HTTP test rather than complex multi-step sequences.


END BIFROST-PROMPT
