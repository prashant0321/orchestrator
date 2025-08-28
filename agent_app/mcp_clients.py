import requests
import json
from typing import Dict, List, Any, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.server_config = settings.MCP_SERVERS.get(server_name)
        if not self.server_config:
            raise ValueError(f"MCP server '{server_name}' not configured")
        
        self.base_url = self.server_config['url']
        self.capabilities = self.server_config['capabilities']
    
    async def execute_ability(self, ability_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an ability on the MCP server"""
        try:
            payload = {
                'ability': ability_name,
                'parameters': parameters,
                'server_capabilities': self.capabilities
            }
            
            response = requests.post(
                f"{self.base_url}/execute",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully executed {ability_name} on {self.server_name}")
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'server': self.server_name,
                    'ability': ability_name
                }
            else:
                logger.error(f"Failed to execute {ability_name} on {self.server_name}: {response.text}")
                return {
                    'success': False,
                    'error': f"Server error: {response.status_code}",
                    'server': self.server_name,
                    'ability': ability_name
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error executing {ability_name} on {self.server_name}: {str(e)}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}",
                'server': self.server_name,
                'ability': ability_name
            }

class MCPOrchestrator:
    def __init__(self):
        self.atlas_client = MCPClient('atlas')
        self.common_client = MCPClient('common')
    
    def get_client(self, server_name: str) -> MCPClient:
        """Get the appropriate MCP client"""
        if server_name == 'atlas':
            return self.atlas_client
        elif server_name == 'common':
            return self.common_client
        else:
            raise ValueError(f"Unknown MCP server: {server_name}")
    
    async def execute_abilities(self, abilities: List[str], server_name: str, state: AgentState) -> List[Dict[str, Any]]:
        """Execute multiple abilities on a specific MCP server"""
        client = self.get_client(server_name)
        results = []
        
        for ability in abilities:
            # Prepare parameters based on current state
            parameters = self._prepare_parameters_for_ability(ability, state)
            result = await client.execute_ability(ability, parameters)
            results.append(result)
        
        return results
    
    def _prepare_parameters_for_ability(self, ability: str, state: AgentState) -> Dict[str, Any]:
        """Prepare parameters for specific abilities based on current state"""
        base_params = {
            'ticket_id': state.ticket_id,
            'customer_name': state.customer_name,
            'customer_email': state.customer_email,
            'priority': state.priority
        }
        
        # Ability-specific parameter mapping
        ability_params = {
            'accept_payload': {'query': state.original_query},
            'parse_request_text': {'text': state.original_query},
            'extract_entities': {'text': state.original_query},
            'normalize_fields': base_params,
            'enrich_records': {**base_params, 'entities': state.extracted_entities},
            'clarify_question': {'original_query': state.original_query, 'entities': state.extracted_entities},
            'knowledge_base_search': {'query': state.original_query, 'entities': state.extracted_entities},
            'solution_evaluation': {'query': state.original_query, 'kb_results': state.knowledge_base_results},
            'escalation_decision': {'solution_score': state.solution_score, 'priority': state.priority},
            'response_generation': {'solution_data': state.knowledge_base_results, 'customer_query': state.original_query},
            'update_ticket': {**base_params, 'status': 'resolved'},
            'execute_api_calls': {'response_data': state.response_text},
            'output_payload': {'state': state.dict()}
        }
        
        return ability_params.get(ability, base_params)