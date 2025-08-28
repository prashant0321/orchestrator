from agent_app.schemas import StageConfig, StageMode, MCPServer

# Lang Graph Agent Configuration
WORKFLOW_STAGES = {
    'INTAKE': StageConfig(
        name='INTAKE',
        mode=StageMode.DETERMINISTIC,
        abilities=['accept_payload'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Execute intake stage: accept and validate customer payload",
        next_stage='UNDERSTAND'
    ),
    'UNDERSTAND': StageConfig(
        name='UNDERSTAND',
        mode=StageMode.DETERMINISTIC,
        abilities=['parse_request_text', 'extract_entities'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Execute abilities in sequence to understand customer request",
        next_stage='PREPARE'
    ),
    'PREPARE': StageConfig(
        name='PREPARE',
        mode=StageMode.DETERMINISTIC,
        abilities=['normalize_fields', 'enrich_records', 'add_flags_calculations'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Execute preparation abilities to normalize and enrich data",
        next_stage='ASK'
    ),
    'ASK': StageConfig(
        name='ASK',
        mode=StageMode.NON_DETERMINISTIC,
        abilities=['clarify_question'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Determine if clarification is needed based on entity extraction quality",
        next_stage='WAIT',
        condition_field='clarification_needed'
    ),
    'WAIT': StageConfig(
        name='WAIT',
        mode=StageMode.DETERMINISTIC,
        abilities=['extract_answer', 'store_answer'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Wait for and process customer response (simulated)",
        next_stage='RETRIEVE'
    ),
    'RETRIEVE': StageConfig(
        name='RETRIEVE',
        mode=StageMode.DETERMINISTIC,
        abilities=['knowledge_base_search', 'store_data'],
        mcp_server=MCPServer.ATLAS,
        prompt_template="Search knowledge base and store relevant data",
        next_stage='DECIDE'
    ),
    'DECIDE': StageConfig(
        name='DECIDE',
        mode=StageMode.NON_DETERMINISTIC,
        abilities=['solution_evaluation', 'escalation_decision', 'update_payload'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Score solutions and escalate if confidence score < 0.8",
        next_stage='UPDATE',
        condition_field='escalation_required'
    ),
    'UPDATE': StageConfig(
        name='UPDATE',
        mode=StageMode.DETERMINISTIC,
        abilities=['update_ticket', 'close_ticket'],
        mcp_server=MCPServer.ATLAS,
        prompt_template="Update ticket status and close if resolved",
        next_stage='CREATE'
    ),
    'CREATE': StageConfig(
        name='CREATE',
        mode=StageMode.DETERMINISTIC,
        abilities=['response_generation'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Generate customer response based on solution data",
        next_stage='DO'
    ),
    'DO': StageConfig(
        name='DO',
        mode=StageMode.DETERMINISTIC,
        abilities=['execute_api_calls', 'trigger_notifications'],
        mcp_server=MCPServer.ATLAS,
        prompt_template="Execute external API calls and send notifications",
        next_stage='COMPLETE'
    ),
    'COMPLETE': StageConfig(
        name='COMPLETE',
        mode=StageMode.DETERMINISTIC,
        abilities=['output_payload'],
        mcp_server=MCPServer.COMMON,
        prompt_template="Generate final structured output payload",
        next_stage=None
    )
}