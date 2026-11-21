# Host access follow-up

After the CPU packet was prepared, discovery found the separate PC connector
`app_shell_exec`. A single read-only attempt requested `rtk proxy nvidia-smi
--query-gpu=name,driver_version --format=csv,noheader` in the repository with
a10s timeout. It returned:

> MCP tool call requires approval, but approval policy is never

No GPU command output or execution result was obtained. This is a permission
block, not an observed GPU/driver failure. No alternative escalation, host
launch, config write, world write or attempted instrumentation activation
followed. The local execution environment also has no `/dev/nvidia0` or
`/dev/nvidiactl`. Host runtime validation remains unexecuted in this turn.

The Oct5 phase45 physical run, four role-pair audit and ordinary restoration
remain completed saved evidence; they must not be rerun merely to recover
access. The current integer-coordinate candidate is CPU-qualified only.
