"""
Integration test for the application (without GUI).
Tests the integration of components.
"""
import os
import sys
import tempfile
import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_data_repository import CSVDataRepository

def test_integration():
    """Test basic integration of repository and application flow"""
    print("Running integration tests...")
    
    # Create temp CSV
    fd, csv_path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)
    os.remove(csv_path)
    
    try:
        # Initialize repository
        repo = CSVDataRepository(csv_path)
        repo.initialize()
        print("✓ Repository initialized")
        
        # Simulate adding a task
        task1 = {
            'start_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 30.0,
            'ticket': 'TEST-123',
            'title': 'Implemented new feature',
            'system_info': 'Test System',
            'ai_summary': 'Worked on implementing the new feature for 30 minutes',
            'resolved': 'No'
        }
        
        result = repo.log_task(task1)
        assert result, "Failed to log task"
        print("✓ Task logged successfully")
        
        # Get today's tasks
        today_tasks = repo.get_tasks_by_date(datetime.date.today())
        assert len(today_tasks) == 1, f"Expected 1 task, got {len(today_tasks)}"
        assert today_tasks[0]['Title'] == 'Implemented new feature'
        assert today_tasks[0]['Resolved'] == 'No'
        print("✓ Retrieved today's tasks")
        
        # Update resolved status
        task_id = today_tasks[0]['task_id']
        result = repo.update_task_resolved_status(task_id, 'Yes')
        assert result, "Failed to update task status"
        print("✓ Updated task resolved status")
        
        # Verify update
        updated_tasks = repo.get_tasks_by_date(datetime.date.today())
        assert updated_tasks[0]['Resolved'] == 'Yes', "Task not marked as resolved"
        print("✓ Verified task update")
        
        # Add another task
        task2 = {
            'start_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 45.0,
            'ticket': 'TEST-456',
            'title': 'Fixed bug',
            'system_info': 'Test System',
            'ai_summary': 'Fixed a critical bug',
            'resolved': 'Yes'
        }
        
        repo.log_task(task2)
        all_tasks = repo.get_tasks_by_date(datetime.date.today())
        assert len(all_tasks) == 2, f"Expected 2 tasks, got {len(all_tasks)}"
        print("✓ Multiple tasks logged and retrieved")
        
        # Test filtering by date (future date should return empty)
        future_date = datetime.date.today() + datetime.timedelta(days=1)
        future_tasks = repo.get_tasks_by_date(future_date)
        assert len(future_tasks) == 0, f"Expected 0 tasks for future date, got {len(future_tasks)}"
        print("✓ Date filtering works correctly")
        
        print("\n✅ All integration tests passed!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(csv_path):
            os.remove(csv_path)

if __name__ == '__main__':
    success = test_integration()
    sys.exit(0 if success else 1)
