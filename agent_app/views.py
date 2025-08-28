from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import asyncio
import json
import logging

from agent_app.schemas import CustomerSupportInput
from agent_app.lang_graph_agent import LangGraphCustomerSupportAgent
from agent_app.models import CustomerSupportTicket, AgentWorkflowState

logger = logging.getLogger(__name__)

@api_view(['POST'])
def process_support_request(request):
    """
    API endpoint to process customer support requests through Lang Graph Agent
    """
    try:
        # Validate input data
        input_data = CustomerSupportInput(**request.data)
        
        # Create database records
        ticket = CustomerSupportTicket.objects.create(
            customer_name=input_data.customer_name,
            customer_email=input_data.customer_email,
            query=input_data.query,
            priority=input_data.priority.value,
            status='in_progress'
        )
        
        # Update input with ticket ID
        input_data.ticket_id = str(ticket.ticket_id)
        
        # Initialize workflow state
        workflow_state = AgentWorkflowState.objects.create(
            ticket=ticket,
            current_stage='INTAKE',
            state_data={'initialized': True}
        )
        
        # Initialize and run the Lang Graph Agent
        agent = LangGraphCustomerSupportAgent()
        
        # Run the async workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            agent.process_customer_support_request(input_data)
        )
        loop.close()
        
        # Update database with results
        workflow_state.is_complete = result.get('success', False)
        workflow_state.stage_logs = result.get('stage_logs', [])
        workflow_state.state_data.update({
            'final_result': result,
            'completed_at': str(workflow_state.updated_at)
        })
        workflow_state.save()
        
        # Update ticket status
        if result.get('success'):
            ticket.status = 'resolved'
        else:
            ticket.status = 'new'
        ticket.save()
        
        return Response({
            'success': result.get('success', False),
            'ticket_id': str(ticket.ticket_id),
            'workflow_id': str(workflow_state.workflow_id),
            'result': result,
            'message': 'Customer support request processed successfully' if result.get('success') else 'Processing failed'
        }, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error processing support request: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to process customer support request'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_workflow_status(request, workflow_id):
    """
    Get the status of a workflow execution
    """
    try:
        workflow = AgentWorkflowState.objects.get(workflow_id=workflow_id)
        
        return Response({
            'workflow_id': str(workflow.workflow_id),
            'ticket_id': str(workflow.ticket.ticket_id),
            'current_stage': workflow.current_stage,
            'is_complete': workflow.is_complete,
            'stage_logs': workflow.stage_logs,
            'state_data': workflow.state_data,
            'created_at': workflow.created_at,
            'updated_at': workflow.updated_at
        })
        
    except AgentWorkflowState.DoesNotExist:
        return Response({
            'error': 'Workflow not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def demo_run(request):
    """
    Demo endpoint with sample customer query
    """
    sample_input = {
        "customer_name": "John Smith",
        "customer_email": "john.smith@example.com",
        "query": "My internet connection has been slow for the past week. I've tried restarting my router but it's still not working properly. Can you help me fix this issue?",
        "priority": "medium"
    }
    
    # Process the demo request
    return process_support_request(type('Request', (), {'data': sample_input})())