#!/usr/bin/env python3
"""
Demonstration script for the new features.
This simulates the application workflow without requiring a GUI.
"""
import os
import sys
import datetime
import tempfile

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_data_repository import CSVDataRepository

def print_separator():
    print("\n" + "="*70 + "\n")

def demo_new_features():
    """Demonstrate the new features"""
    print("🐑🐈 SheepCat Work Tracker - New Features Demo")
    print_separator()
    
    # Create a temporary CSV for the demo
    fd, csv_path = tempfile.mkstemp(suffix='.csv', prefix='work_log_demo_')
    os.close(fd)
    os.remove(csv_path)
    
    try:
        # Initialize repository
        print("1. Initializing Data Repository (CSV implementation)")
        repo = CSVDataRepository(csv_path)
        repo.initialize()
        print(f"   ✓ CSV file created at: {csv_path}")
        
        print_separator()
        
        # Simulate adding tasks during the day
        print("2. Simulating a work day with multiple tasks...")
        
        tasks = [
            {
                'start_time': '2024-02-19 09:00:00',
                'end_time': '2024-02-19 09:30:00',
                'duration': 30.0,
                'ticket': 'PROJ-101',
                'title': 'Fixed login bug',
                'system_info': 'OS: Linux | Node: dev-machine',
                'ai_summary': 'Resolved a critical authentication bug affecting user login.',
                'resolved': 'No'  # Initially marked as unresolved
            },
            {
                'start_time': '2024-02-19 10:00:00',
                'end_time': '2024-02-19 10:45:00',
                'duration': 45.0,
                'ticket': 'PROJ-102',
                'title': 'Implemented new feature',
                'system_info': 'OS: Linux | Node: dev-machine',
                'ai_summary': 'Added user profile page with avatar upload functionality.',
                'resolved': 'Yes'
            },
            {
                'start_time': '2024-02-19 11:00:00',
                'end_time': '2024-02-19 11:20:00',
                'duration': 20.0,
                'ticket': 'PROJ-103',
                'title': 'Code review',
                'system_info': 'OS: Linux | Node: dev-machine',
                'ai_summary': 'Reviewed pull request for database migration.',
                'resolved': 'No'
            }
        ]
        
        for i, task in enumerate(tasks, 1):
            repo.log_task(task)
            print(f"   ✓ Task {i} logged: {task['title']} ({task['ticket']})")
        
        print_separator()
        
        # Demonstrate retrieving tasks by date
        print("3. Review Work Log - Retrieving today's tasks...")
        today = datetime.date(2024, 2, 19)
        today_tasks = repo.get_tasks_by_date(today)
        
        print(f"\n   Found {len(today_tasks)} tasks for {today}:\n")
        print(f"   {'Time':<8} {'Ticket':<12} {'Title':<30} {'Duration':<10} {'Resolved':<10}")
        print(f"   {'-'*8} {'-'*12} {'-'*30} {'-'*10} {'-'*10}")
        
        for task in today_tasks:
            time_str = task['Start Time'].split()[1][:5] if task['Start Time'] else ''
            print(f"   {time_str:<8} {task['Ticket']:<12} {task['Title']:<30} {task['Duration (Min)']:<10} {task['Resolved']:<10}")
        
        print_separator()
        
        # Demonstrate updating resolved status
        print("4. Review Work Log - Updating task status...")
        print("\n   Scenario: We completed fixing the login bug (PROJ-101)")
        print("   but forgot to mark it as resolved. Let's update it!\n")
        
        # Find the task
        unresolved_task = None
        for task in today_tasks:
            if task['Ticket'] == 'PROJ-101':
                unresolved_task = task
                break
        
        if unresolved_task:
            print(f"   Before: {unresolved_task['Title']} - Resolved: {unresolved_task['Resolved']}")
            
            # Update status
            task_id = unresolved_task['task_id']
            repo.update_task_resolved_status(task_id, 'Yes')
            
            # Retrieve updated task
            updated_tasks = repo.get_tasks_by_date(today)
            updated_task = next(t for t in updated_tasks if t['Ticket'] == 'PROJ-101')
            
            print(f"   After:  {updated_task['Title']} - Resolved: {updated_task['Resolved']}")
            print("\n   ✓ Task status updated successfully!")
        
        print_separator()
        
        # Show statistics
        print("5. Work Log Statistics...")
        resolved_count = sum(1 for t in updated_tasks if t['Resolved'] == 'Yes')
        total_duration = sum(float(t['Duration (Min)']) for t in updated_tasks)
        
        print(f"\n   Total tasks logged: {len(updated_tasks)}")
        print(f"   Tasks resolved: {resolved_count}/{len(updated_tasks)}")
        print(f"   Total time tracked: {total_duration} minutes")
        
        print_separator()
        
        # Demonstrate future extensibility
        print("6. Future-Proof Architecture")
        print("\n   The repository pattern allows easy migration to other data sources:")
        print("\n   Current: CSVDataRepository (CSV file storage)")
        print("   Future options:")
        print("   - SQLDataRepository (PostgreSQL, MySQL, SQLite)")
        print("   - MongoDataRepository (MongoDB, DocumentDB)")
        print("   - APIDataRepository (REST API for centralized user management)")
        print("\n   ✓ Just swap the repository class - no other code changes needed!")
        
        print_separator()
        
        print("✅ Demo completed successfully!")
        print(f"\nDemo CSV file saved at: {csv_path}")
        print("You can inspect it to see the data structure.\n")
        
        return csv_path
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(csv_path):
            os.remove(csv_path)
        return None

if __name__ == '__main__':
    csv_file = demo_new_features()
    
    if csv_file and os.path.exists(csv_file):
        print(f"To view the CSV file: cat {csv_file}")
        print(f"To clean up: rm {csv_file}")
