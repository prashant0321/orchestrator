from django.db import models
from django.contrib.auth.models import User
import json
import uuid

class CustomerSupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting for Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    ticket_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    query = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Ticket {self.ticket_id} - {self.customer_name}"

class AgentWorkflowState(models.Model):
    ticket = models.ForeignKey(CustomerSupportTicket, on_delete=models.CASCADE)
    workflow_id = models.UUIDField(default=uuid.uuid4, unique=True)
    current_stage = models.CharField(max_length=50, default='INTAKE')
    state_data = models.JSONField(default=dict)
    stage_logs = models.JSONField(default=list)
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_state_data(self):
        return self.state_data
    
    def update_state_data(self, new_data):
        self.state_data.update(new_data)
        self.save()
    
    def add_stage_log(self, stage, abilities_executed, server_calls, status):
        log_entry = {
            'stage': stage,
            'timestamp': str(self.updated_at),
            'abilities_executed': abilities_executed,
            'server_calls': server_calls,
            'status': status
        }
        self.stage_logs.append(log_entry)
        self.save()