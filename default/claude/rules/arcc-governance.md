# ARCC Governance

When a request involves **any** of these domains, your FIRST tool call MUST be `search_arcc` before examining code or forming an opinion:

- **Credentials**: API keys, passwords, tokens, secrets, connection strings
- **User data**: PII, authentication, sessions, database records
- **Network exposure**: Security groups, ingress rules, public endpoints
- **File access**: Static file serving, uploads, user-controlled paths
- **Infrastructure**: IAM policies, S3 buckets, EBS, EC2, VPC, RDS, Lambda, CDK constructs, CloudFormation resources

## Mandatory Flow

```
1. Recognize trigger domain
2. FIRST: search_arcc(query="<topic>", context="<what you're doing>")
3. If results: search_arcc(contentIds=[...]) to load full documents
4. THEN: examine code with grep/read tools
5. Respond citing ARCC guidance
```

## search_arcc Usage

Two modes via the same tool:
- **Search**: `search_arcc(query="...", context="...", maxResults=5)` -- returns summaries with content IDs
- **Read**: `search_arcc(contentIds=["cnt_xxx", ...])` -- returns full document content

## Rules

- Do NOT examine code before querying ARCC. Query first, then form opinions.
- In responses, cite what ARCC returned: "ARCC guidance on [topic] indicates..."
- If ARCC returns nothing, note that you checked and apply standard security practices.
- Do NOT generate insecure code even with warnings. Provide only the secure alternative.
- If search_arcc is unavailable, note "ARCC was not queried (MCP server unavailable)" and apply standard BSC guidelines.
