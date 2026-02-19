"""
Abstract data repository for work log data.
This allows for different data sources (CSV, SQL, NoSQL, API) in the future.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import datetime


class DataRepository(ABC):
    """Abstract base class for data repositories"""
    
    @abstractmethod
    def initialize(self):
        """Initialize the data store (e.g., create tables, files, etc.)"""
        pass
    
    @abstractmethod
    def log_task(self, task_data: Dict) -> bool:
        """
        Log a single task entry.
        
        Args:
            task_data: Dictionary containing:
                - start_time: datetime
                - end_time: datetime
                - duration: float (minutes)
                - ticket: str
                - title: str
                - system_info: str
                - ai_summary: str
                - resolved: str ("Yes" or "No")
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_tasks_by_date(self, date: datetime.date) -> List[Dict]:
        """
        Get all tasks for a specific date.
        
        Args:
            date: The date to retrieve tasks for
        
        Returns:
            List of task dictionaries
        """
        pass
    
    @abstractmethod
    def get_tasks_since(self, start_time: datetime.datetime) -> List[Dict]:
        """
        Get all tasks since a specific datetime.
        
        Args:
            start_time: The datetime to start from
        
        Returns:
            List of task dictionaries
        """
        pass
    
    @abstractmethod
    def update_task_resolved_status(self, task_id: str, resolved: str) -> bool:
        """
        Update the resolved status of a task.
        
        Args:
            task_id: Unique identifier for the task (implementation specific)
            resolved: "Yes" or "No"
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks in the data store.
        
        Returns:
            List of task dictionaries
        """
        pass
