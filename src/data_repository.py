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
    def update_task_timing(self, task_id: str, end_time: str, duration: float) -> bool:
        """
        Update the end time and duration of an already-saved task.

        Called when the *next* task is logged so that the previous task's
        duration reflects the actual time spent on it (chain-based timing).

        Args:
            task_id: Unique identifier for the task (implementation specific)
            end_time: ISO-formatted end time string ("%Y-%m-%d %H:%M:%S")
            duration: Actual duration in minutes (float)

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def update_tasks_timing_by_start_time(
        self, start_time_str: str, end_time_str: str, duration: float
    ) -> bool:
        """
        Update the end time and duration of all tasks sharing a given start time.

        Multiple-ticket tasks produce one CSV row per ticket, all with the same
        start time.  This method updates every such row in a single pass.

        Args:
            start_time_str: ``Start Time`` value to match (``"%Y-%m-%d %H:%M:%S"``).
            end_time_str: New end time string in the same format.
            duration: Duration in minutes to write to every matching row.

        Returns:
            bool: True if at least one row was updated, False otherwise.
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

    @abstractmethod
    def search_tasks(self, keyword: str, start_date: Optional[datetime.date] = None,
                     end_date: Optional[datetime.date] = None) -> List[Dict]:
        """
        Search tasks whose title or AI summary contains the given keyword.

        Args:
            keyword: Case-insensitive substring to look for in Title and AI Summary.
            start_date: If provided, only return tasks on or after this date.
            end_date: If provided, only return tasks on or before this date.

        Returns:
            List of matching task dictionaries, oldest first.
        """
        pass
