"""
Tests for the data repository implementations.
"""
import os
import sys
import tempfile
import datetime
import unittest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_data_repository import CSVDataRepository


class TestCSVDataRepository(unittest.TestCase):
    def setUp(self):
        """Create a temporary CSV file for testing"""
        # Create a temp file descriptor and close it to get just the path
        fd, self.csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        # Remove the file so repository can create it fresh
        os.remove(self.csv_path)
        self.repo = CSVDataRepository(self.csv_path)
    
    def tearDown(self):
        """Clean up temporary file"""
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
    
    def test_initialize_creates_file(self):
        """Test that initialize creates a CSV file with headers"""
        self.repo.initialize()
        self.assertTrue(os.path.exists(self.csv_path))
        
        # Check headers
        with open(self.csv_path, 'r') as f:
            headers = f.readline().strip()
            expected = "Start Time,End Time,Duration (Min),Ticket,Title,System Info,AI Summary,Resolved"
            self.assertEqual(headers, expected)
    
    def test_log_task(self):
        """Test logging a task"""
        self.repo.initialize()
        
        task_data = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-123',
            'title': 'Test Task',
            'system_info': 'Test System',
            'ai_summary': 'Task summary',
            'resolved': 'Yes'
        }
        
        result = self.repo.log_task(task_data)
        self.assertTrue(result)
        
        # Verify task was logged
        tasks = self.repo.get_all_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['Title'], 'Test Task')
        self.assertEqual(tasks[0]['Ticket'], 'TEST-123')
        self.assertEqual(tasks[0]['Resolved'], 'Yes')
    
    def test_get_tasks_by_date(self):
        """Test retrieving tasks by date"""
        self.repo.initialize()
        
        # Add tasks on different dates
        task1 = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-1',
            'title': 'Task 1',
            'system_info': 'Test',
            'ai_summary': 'Summary 1',
            'resolved': 'Yes'
        }
        
        task2 = {
            'start_time': '2024-01-16 11:00:00',
            'end_time': '2024-01-16 11:30:00',
            'duration': 30.0,
            'ticket': 'TEST-2',
            'title': 'Task 2',
            'system_info': 'Test',
            'ai_summary': 'Summary 2',
            'resolved': 'No'
        }
        
        self.repo.log_task(task1)
        self.repo.log_task(task2)
        
        # Get tasks for specific date
        date1 = datetime.date(2024, 1, 15)
        tasks_on_date1 = self.repo.get_tasks_by_date(date1)
        
        self.assertEqual(len(tasks_on_date1), 1)
        self.assertEqual(tasks_on_date1[0]['Title'], 'Task 1')
        
        date2 = datetime.date(2024, 1, 16)
        tasks_on_date2 = self.repo.get_tasks_by_date(date2)
        
        self.assertEqual(len(tasks_on_date2), 1)
        self.assertEqual(tasks_on_date2[0]['Title'], 'Task 2')
    
    def test_update_task_resolved_status(self):
        """Test updating the resolved status of a task"""
        self.repo.initialize()
        
        # Log a task
        task_data = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-123',
            'title': 'Test Task',
            'system_info': 'Test System',
            'ai_summary': 'Task summary',
            'resolved': 'No'
        }
        self.repo.log_task(task_data)
        
        # Get the task
        tasks = self.repo.get_all_tasks()
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0]['task_id']
        
        # Update status
        result = self.repo.update_task_resolved_status(task_id, 'Yes')
        self.assertTrue(result)
        
        # Verify update
        tasks = self.repo.get_all_tasks()
        self.assertEqual(tasks[0]['Resolved'], 'Yes')
    
    def test_get_tasks_since(self):
        """Test retrieving tasks since a specific datetime"""
        self.repo.initialize()
        
        # Add tasks at different times
        task1 = {
            'start_time': '2024-01-15 09:00:00',
            'end_time': '2024-01-15 09:30:00',
            'duration': 30.0,
            'ticket': 'TEST-1',
            'title': 'Task 1',
            'system_info': 'Test',
            'ai_summary': 'Summary 1',
            'resolved': 'Yes'
        }
        
        task2 = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-2',
            'title': 'Task 2',
            'system_info': 'Test',
            'ai_summary': 'Summary 2',
            'resolved': 'No'
        }
        
        task3 = {
            'start_time': '2024-01-15 11:00:00',
            'end_time': '2024-01-15 11:30:00',
            'duration': 30.0,
            'ticket': 'TEST-3',
            'title': 'Task 3',
            'system_info': 'Test',
            'ai_summary': 'Summary 3',
            'resolved': 'Yes'
        }
        
        self.repo.log_task(task1)
        self.repo.log_task(task2)
        self.repo.log_task(task3)
        
        # Get tasks since 10:00
        since_time = datetime.datetime(2024, 1, 15, 10, 0, 0)
        tasks = self.repo.get_tasks_since(since_time)
        
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['Title'], 'Task 2')
        self.assertEqual(tasks[1]['Title'], 'Task 3')


if __name__ == '__main__':
    unittest.main()
