from langgraph import StateGraph, END
from typing import Dict, List, Any
import asyncio
import logging
from datetime import datetime

from agent_app.schemas import AgentState, CustomerSupportInput
from agent_app.workflow_config import WORKFLOW_STAGES
from agent_app.mcp_clients import MCPOrchestrator
from agent_app.models import AgentWorkflowState, CustomerSupportTicket

logger = logging.getLogger(__name__)

class LangGraphCustomerSupportAgent:
    """
    Langie - The Lang Graph Customer Support Agent
    
    A structured and logical agent that thinks in stages, carries forward state variables,
    and orchestrates MCP clients for ability execution.
    """
    
    def __init__(self):
        self.mcp_orchestrator = MCPOrchestrator()
        self.workflow_graph = self._build_workflow_graph()
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the Lang Graph workflow with all 11 stages"""
        graph = StateGraph(AgentState)
        
        # Add all stage nodes
        for stage_name, stage_config in WORKFLOW_STAGES.items():
            if stage_config.mode.value == "deterministic":
                graph.add_node(stage_name, self._execute_deterministic_stage)
            else:
                graph.add_node(stage_name, self._execute_non_deterministic_stage)
        
        # Add edges based on stage configuration
        graph.set_entry_point("INTAKE")
        
        for stage_name, stage_config in WORKFLOW_STAGES.items():
            if stage_config.next_stage:
                if stage_config.condition_field:
                    # Conditional routing for non-deterministic stages
                    graph.add_conditional_edges(
                        stage_name,
                        self._route_condition,
                        {
                            True: stage_config.next_stage,
                            False: "COMPLETE"  # Skip to completion if condition not met
                        }
                    )
                else:
                    graph.add_edge(stage_name, stage_config.next_stage)
            else:
                graph.add_edge(stage_name, END)
        
        return graph.compile()
    
    async def _execute_deterministic_stage(self, state: AgentState) -> AgentState:
        """Execute abilities sequentially for deterministic stages"""
        current_stage = state.current_stage
        stage_config = WORKFLOW_STAGES[current_stage]
        
        logger.info(f"🔄 Executing deterministic stage: {current_stage}")
        
        try:
            # Execute abilities in sequence
            results = await self.mcp_orchestrator.execute_abilities(
                abilities=stage_config.abilities,
                server_name=stage_config.mcp_server.value,
                state=state
            )
            
            # Update state based on stage results
            state = self._update_state_from_results(state, current_stage, results)
            
            # Log stage execution
            self._log_stage_execution(state, current_stage, stage_config.abilities, results, "SUCCESS")
            
            # Move to next stage
            if stage_config.next_stage:
                state.current_stage = stage_config.next_stage
            
        except Exception as e:
            logger.error(f"❌ Error in stage {current_stage}: {str(e)}")
            state.errors.append(f"Stage {current_stage}: {str(e)}")
            self._log_stage_execution(state, current_stage, stage_config.abilities, [], "ERROR")
        
        return state
    
    async def _execute_non_deterministic_stage(self, state: AgentState) -> AgentState:
        """Execute abilities dynamically based on context for non-deterministic stages"""
        current_stage = state.current_stage
        stage_config = WORKFLOW_STAGES[current_stage]
        
        logger.info(f"🎯 Executing non-deterministic stage: {current_stage}")
        
        try:
            # Dynamic ability selection based on context
            abilities_to_execute = self._select_abilities_dynamically(state, stage_config)
            
            if abilities_to_execute:
                results = await self.mcp_orchestrator.execute_abilities(
                    abilities=abilities_to_execute,
                    server_name=stage_config.mcp_server.value,
                    state=state
                )
                
                # Update state based on results
                state = self._update_state_from_results(state, current_stage, results)
                
                self._log_stage_execution(state, current_stage, abilities_to_execute, results, "SUCCESS")
            else:
                logger.info(f"⏭️ Skipping {current_stage} - no abilities needed")
                self._log_stage_execution(state, current_stage, [], [], "SKIPPED")
            
            # Move to next stage
            if stage_config.next_stage:
                state.current_stage = stage_config.next_stage
                
        except Exception as e:
            logger.error(f"❌ Error in stage {current_stage}: {str(e)}")
            state.errors.append(f"Stage {current_stage}: {str(e)}")
            self._log_stage_execution(state, current_stage, stage_config.abilities, [], "ERROR")
        
        return state
    
    def _select_abilities_dynamically(self, state: AgentState, stage_config) -> List[str]:
        """Select abilities dynamically based on current state and context"""
        if stage_config.name == "ASK":
            # Determine if clarification is needed based on entity extraction quality
            if state.extracted_entities:
                entity_confidence = state.extracted_entities.get('confidence', 0.7)
                if entity_confidence < 0.8:
                    state.clarification_needed = True
                    return ['clarify_question']
            state.clarification_needed = False
            return []
        
        elif stage_config.name == "DECIDE":
            # Always evaluate solution, then decide on escalation
            abilities = ['solution_evaluation']
            
            # Simulate solution scoring (in real implementation, this would come from MCP result)
            state.solution_score = 0.75  # Mock score
            
            if state.solution_score < 0.8 or state.priority in ['high', 'critical']:
                state.escalation_required = True
                abilities.extend(['escalation_decision', 'update_payload'])
            else:
                state.escalation_required = False
                abilities.append('update_payload')
            
            return abilities
        
        # Default: return all abilities for the stage
        return stage_config.abilities
    
    def _update_state_from_results(self, state: AgentState, stage: str, results: List[Dict[str, Any]]) -> AgentState:
        """Update agent state based on stage execution results"""
        for result in results:
            if not result.get('success', False):
                continue
                
            ability = result.get('ability')
            data = result.get('data', {})
            
            # Update state based on ability results
            if ability == 'accept_payload':
                # Payload accepted, state already initialized
                pass
            elif ability == 'parse_request_text':
                state.parsed_request = data
            elif ability == 'extract_entities':
                state.extracted_entities = data
            elif ability == 'normalize_fields':
                state.normalized_fields = data
            elif ability == 'enrich_records':
                state.enriched_data = data
            elif ability == 'clarify_question':
                # In real implementation, this would trigger customer interaction
                pass
            elif ability == 'extract_answer':
                state.customer_answer = data.get('answer', '')
            elif ability == 'knowledge_base_search':
                state.knowledge_base_results = data.get('results', [])
            elif ability == 'solution_evaluation':
                state.solution_score = data.get('score', 0.0)
            elif ability == 'response_generation':
                state.response_text = data.get('response', '')
            elif ability == 'execute_api_calls':
                state.api_results = data
            elif ability == 'output_payload':
                state.final_payload = data
        
        return state
    
    def _log_stage_execution(self, state: AgentState, stage: str, abilities: List[str], 
                           results: List[Dict[str, Any]], status: str):
        """Log stage execution details"""
        server_calls = []
        for result in results:
            server_calls.append({
                'server': result.get('server', 'unknown'),
                'ability': result.get('ability', 'unknown'),
                'success': result.get('success', False)
            })
        
        log_entry = {
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'abilities_executed': abilities,
            'server_calls': server_calls,
            'status': status
        }
        
        state.stage_logs.append(log_entry)
        logger.info(f"📝 Logged execution for stage {stage}: {status}")
    
    def _route_condition(self, state: AgentState) -> bool:
        """Route based on condition field for non-deterministic stages"""
        if state.current_stage == "ASK":
            return state.clarification_needed or False
        elif state.current_stage == "DECIDE":
            return not (state.escalation_required or False)  # Continue if no escalation needed
        return True
    
    async def process_customer_support_request(self, input_data: CustomerSupportInput) -> Dict[str, Any]:
        """Main entry point for processing customer support requests"""
        logger.info(f"🚀 Starting customer support workflow for: {input_data.customer_name}")
        
        # Initialize agent state
        initial_state = AgentState(
            ticket_id=input_data.ticket_id or f"TKT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            customer_name=input_data.customer_name,
            customer_email=input_data.customer_email,
            original_query=input_data.query,
            priority=input_data.priority.value,
            current_stage="INTAKE"
        )
        
        try:
            # Execute the workflow graph
            final_state = await self.workflow_graph.ainvoke(initial_state)
            
            logger.info(f"✅ Workflow completed for ticket {final_state.ticket_id}")
            
            return {
                'success': True,
                'ticket_id': final_state.ticket_id,
                'final_payload': final_state.final_payload,
                'stage_logs': final_state.stage_logs,
                'errors': final_state.errors
            }
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'ticket_id': initial_state.ticket_id,
                'stage_logs': initial_state.stage_logs
            }