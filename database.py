import mysql.connector
import os
import logging
import json
from typing import Dict, List, Optional

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'mk0492'),
    'database': os.getenv('DB_NAME', 'academic_analyzer'),
    'charset': 'utf8mb4',
    'autocommit': True,
    'connection_timeout': 10,
    'connect_timeout': 10
}

def get_db_connection():
    """Create and return database connection"""
    try:
        logging.info(f"Attempting to connect to database: {DB_CONFIG['host']}:{DB_CONFIG.get('port', 3306)}")
        connection = mysql.connector.connect(**DB_CONFIG)
        logging.info("Database connection successful")
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Database connection error: {e}")
        logging.error(f"Connection config: host={DB_CONFIG['host']}, user={DB_CONFIG['user']}, database={DB_CONFIG['database']}")
        raise

def test_database_connection():
    """Test database connection and basic queries"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM launched_results")
        launched_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sections")
        section_count = cursor.fetchone()[0]
        
        logging.info(f"Database test successful - Launches: {launched_count}, Students: {student_count}, Sections: {section_count}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        logging.error(f"Database test failed: {e}")
        return False

def get_sections() -> List[str]:
    """Get all available sections from launched results"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        logging.info("=== DEBUG: Getting sections ===")
        
        # First, check if we have any launched_results at all
        cursor.execute("SELECT COUNT(*) FROM launched_results")
        total_launches = cursor.fetchone()[0]
        logging.info(f"Total launched_results: {total_launches}")
        
        # Check active launched_results
        cursor.execute("SELECT COUNT(*) FROM launched_results WHERE status = 'active'")
        active_launches = cursor.fetchone()[0]
        logging.info(f"Active launched_results: {active_launches}")
        
        # Check sections table
        cursor.execute("SELECT COUNT(*) FROM sections")
        total_sections = cursor.fetchone()[0]
        logging.info(f"Total sections: {total_sections}")
        
        sections = []
        
        if active_launches > 0:
            # Get sections that have active launched results
            query = """
            SELECT DISTINCT s.section_name
            FROM sections s
            JOIN launched_results lr ON s.id = lr.section_id
            WHERE lr.status = 'active'
            ORDER BY s.section_name
            """
            
            logging.info(f"Executing query: {query}")
            cursor.execute(query)
            results = cursor.fetchall()
            
            logging.info(f"Query results: {results}")
            
            for row in results:
                sections.append(row[0])  # section_name
                logging.info(f"Found section with active results: {row[0]}")
        
        # If no sections with active results, get all sections (for testing)
        if not sections:
            logging.info("No sections with active results found, getting all sections")
            cursor.execute("SELECT DISTINCT section_name FROM sections ORDER BY section_name")
            fallback_results = cursor.fetchall()
            sections = [row[0] for row in fallback_results]
            logging.info(f"All sections: {sections}")
            
            # If still no sections, add a test section
            if not sections:
                logging.warning("No sections found in database at all")
                sections = ["Test Section"]
        
        cursor.close()
        connection.close()
        
        logging.info(f"Final sections list: {sections}")
        return sections
    
    except Exception as e:
        logging.error(f"Error fetching sections: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return ["Database Error"]

def verify_student_login(section: str, name: str, roll_number: str) -> Optional[Dict]:
    """Verify student login credentials and check if they have active results"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        logging.info(f"=== DEBUG: Verifying student login ===")
        logging.info(f"Section: '{section}', Name: '{name}', Roll: '{roll_number}'")
        
        # First, get the student with case-insensitive matching
        query = """
        SELECT s.id, s.student_name as name, sec.section_name as section, s.roll_number 
        FROM students s
        JOIN sections sec ON s.section_id = sec.id
        WHERE LOWER(sec.section_name) = LOWER(%s) 
        AND LOWER(TRIM(s.student_name)) = LOWER(TRIM(%s)) 
        AND LOWER(TRIM(s.roll_number)) = LOWER(TRIM(%s))
        """
        
        logging.info(f"Student query: {query}")
        cursor.execute(query, (section, name, roll_number))
        student = cursor.fetchone()
        
        logging.info(f"Student query result: {student}")
        
        if not student:
            # Debug: Let's check what students exist in this section
            cursor.execute("""
                SELECT s.student_name, s.roll_number, sec.section_name 
                FROM students s 
                JOIN sections sec ON s.section_id = sec.id 
                WHERE LOWER(sec.section_name) = LOWER(%s) 
                LIMIT 10
            """, (section,))
            existing_students = cursor.fetchall()
            logging.info(f"Existing students in section '{section}': {existing_students}")
            
            cursor.close()
            connection.close()
            return None
        
        # Check if student has any active results
        check_results_query = """
        SELECT COUNT(*) as result_count, lr.launch_name, lr.status
        FROM student_web_results swr
        JOIN launched_results lr ON swr.launch_id = lr.id
        WHERE swr.student_id = %s AND lr.status = 'active'
        GROUP BY lr.launch_name, lr.status
        """
        
        logging.info(f"Results check query: {check_results_query}")
        cursor.execute(check_results_query, (student['id'],))
        result_check = cursor.fetchone()
        
        logging.info(f"Results check result: {result_check}")
        
        if not result_check or result_check['result_count'] == 0:
            # Let's check if there are any results for this student (active or not)
            cursor.execute("""
                SELECT lr.launch_name, lr.status, lr.launch_date
                FROM student_web_results swr
                JOIN launched_results lr ON swr.launch_id = lr.id
                WHERE swr.student_id = %s
                ORDER BY lr.launch_date DESC
            """, (student['id'],))
            all_results = cursor.fetchall()
            logging.info(f"All results for student {student['id']}: {all_results}")
            
            cursor.close()
            connection.close()
            return None
        
        logging.info(f"Student verified: {student['name']} with {result_check['result_count']} active results")
        
        cursor.close()
        connection.close()
        
        return student
    
    except Exception as e:
        logging.error(f"Error verifying student login: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def extract_subject_name(full_name: str, component_type: str) -> str:
    """Extract subject name from component name using multiple patterns"""
    
    # Common patterns to remove
    patterns_to_remove = [
        ' - Internal', ' - External',
        ' Internal', ' External',
        ' - I', ' - E',
        ' I', ' E',
        ' (Internal)', ' (External)',
        ' Int', ' Ext',
        ' IA', ' ESE',
        ' Mid', ' Final',
        ' Test', ' Exam'
    ]
    
    subject_name = full_name
    
    # Try to remove common patterns
    for pattern in patterns_to_remove:
        if pattern.lower() in subject_name.lower():
            # Case-insensitive replacement
            import re
            subject_name = re.sub(re.escape(pattern), '', subject_name, flags=re.IGNORECASE)
            break
    
    # If no pattern matched, try to extract based on component type
    if subject_name == full_name and component_type:
        if 'internal' in component_type.lower():
            subject_name = full_name.replace('Internal', '').replace('internal', '')
        elif 'external' in component_type.lower():
            subject_name = full_name.replace('External', '').replace('external', '')
    
    # Clean up the result
    subject_name = subject_name.strip(' -()').strip()
    
    # If we couldn't extract a clean subject name, use the full name
    if not subject_name or len(subject_name) < 2:
        subject_name = full_name
    
    return subject_name

def is_internal_component(component_type: str, component_name: str) -> bool:
    """Determine if a component is internal assessment"""
    type_lower = component_type.lower()
    name_lower = component_name.lower()
    
    internal_keywords = ['internal', 'ia', 'mid', 'test', 'assignment', 'quiz', 'practical']
    
    return any(keyword in type_lower or keyword in name_lower for keyword in internal_keywords)

def is_external_component(component_type: str, component_name: str) -> bool:
    """Determine if a component is external assessment"""
    type_lower = component_type.lower()
    name_lower = component_name.lower()
    
    external_keywords = ['external', 'ese', 'final', 'exam', 'theory', 'end']
    
    return any(keyword in type_lower or keyword in name_lower for keyword in external_keywords)

def calculate_subject_pass_status(subject_data, overall_percentage):
    """Calculate if a subject is passed based on various criteria"""
    
    # Minimum percentage required to pass (configurable)
    MIN_OVERALL_PERCENTAGE = 40.0
    MIN_INTERNAL_PERCENTAGE = 40.0  # If internal exists
    MIN_EXTERNAL_PERCENTAGE = 40.0  # If external exists
    
    # Check overall percentage
    if overall_percentage < MIN_OVERALL_PERCENTAGE:
        return False
    
    # Check internal marks if present
    if subject_data['has_internal'] and subject_data['internal_max'] > 0:
        internal_percentage = (subject_data['internal_marks'] / subject_data['internal_max']) * 100
        if internal_percentage < MIN_INTERNAL_PERCENTAGE:
            return False
    
    # Check external marks if present
    if subject_data['has_external'] and subject_data['external_max'] > 0:
        external_percentage = (subject_data['external_marks'] / subject_data['external_max']) * 100
        if external_percentage < MIN_EXTERNAL_PERCENTAGE:
            return False
    
    return True

def calculate_sgpa_from_subjects(subjects_list):
    """Calculate SGPA based on subject grades"""
    if not subjects_list:
        return 0.0
    
    grade_points = {
        'A+': 10, 'A': 9, 'B+': 8, 'B': 7, 
        'C+': 6, 'C': 5, 'D': 4, 'F': 0
    }
    
    total_points = 0
    total_subjects = 0
    
    for subject in subjects_list:
        grade = subject.get('grade', 'F')
        points = grade_points.get(grade, 0)
        total_points += points
        total_subjects += 1
    
    return round(total_points / total_subjects, 2) if total_subjects > 0 else 0.0

def get_performance_analysis_subjects(subjects_list, components_list):
    """Enhanced performance analysis for multiple subjects"""
    if not subjects_list:
        return {
            'performance_level': 'No Data',
            'strongest_subject': 'N/A',
            'weakest_subject': 'N/A',
            'subjects_passed': 0,
            'subjects_failed': 0,
            'recommendation': 'No data available for analysis'
        }
    
    # Calculate metrics
    avg_percentage = sum(subject['percentage'] for subject in subjects_list) / len(subjects_list)
    strongest_subject = max(subjects_list, key=lambda x: x['percentage'])
    weakest_subject = min(subjects_list, key=lambda x: x['percentage'])
    
    subjects_passed = sum(1 for subject in subjects_list if subject['is_passing'])
    subjects_failed = len(subjects_list) - subjects_passed
    
    # Determine performance level
    if avg_percentage >= 85:
        performance_level = 'Excellent'
    elif avg_percentage >= 75:
        performance_level = 'Very Good'
    elif avg_percentage >= 65:
        performance_level = 'Good'
    elif avg_percentage >= 50:
        performance_level = 'Average'
    else:
        performance_level = 'Needs Improvement'
    
    # Generate recommendation
    if subjects_failed > 0:
        failed_subjects = [s['subject_name'] for s in subjects_list if not s['is_passing']]
        recommendation = f"Focus on improving {', '.join(failed_subjects)} to pass all subjects"
    elif avg_percentage >= 85:
        recommendation = "Excellent performance across all subjects! Keep up the great work"
    elif weakest_subject['percentage'] < 60:
        recommendation = f"Good overall performance. Focus on {weakest_subject['subject_name']} for better results"
    else:
        recommendation = "Consistent performance across subjects. Maintain the good work"
    
    return {
        'performance_level': performance_level,
        'strongest_subject': f"{strongest_subject['subject_name']} ({strongest_subject['percentage']:.1f}%)",
        'weakest_subject': f"{weakest_subject['subject_name']} ({weakest_subject['percentage']:.1f}%)",
        'subjects_passed': subjects_passed,
        'subjects_failed': subjects_failed,
        'average_percentage': round(avg_percentage, 1),
        'recommendation': recommendation
    }

def get_student_results(student_id: int) -> Optional[Dict]:
    """Get complete results for a student from launched results"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get student info
        query = """
        SELECT s.id, s.student_name as name, sec.section_name as section, s.roll_number 
        FROM students s
        JOIN sections sec ON s.section_id = sec.id
        WHERE s.id = %s
        """
        cursor.execute(query, (student_id,))
        student = cursor.fetchone()
        
        if not student:
            logging.error(f"Student not found with ID: {student_id}")
            cursor.close()
            connection.close()
            return None
        
        # Get the most recent active result for this student
        results_query = """
        SELECT swr.result_data, lr.launch_name, lr.launch_date
        FROM student_web_results swr
        JOIN launched_results lr ON swr.launch_id = lr.id
        WHERE swr.student_id = %s AND lr.status = 'active'
        ORDER BY lr.launch_date DESC
        LIMIT 1
        """
        
        cursor.execute(results_query, (student_id,))
        result_row = cursor.fetchone()
        
        if not result_row:
            logging.error(f"No active results found for student ID: {student_id}")
            cursor.close()
            connection.close()
            return None
        
        # Parse the JSON result data
        try:
            result_data = json.loads(result_row['result_data'])
            logging.info(f"Parsed result data for student {student_id}")
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing result JSON: {e}")
            cursor.close()
            connection.close()
            return None
        
        # Process individual components
        components_list = []
        components = result_data.get('components', [])
        
        for component in components:
            component_name = component.get('name', 'Unknown')
            component_type = component.get('type', 'Unknown')
            obtained_marks = component.get('obtained_marks', 0)
            max_marks = component.get('max_marks', 0)
            percentage = (obtained_marks / max_marks * 100) if max_marks > 0 else 0
            
            component_entry = {
                'component_name': component_name,
                'type': component_type,
                'obtained_marks': obtained_marks,
                'max_marks': max_marks,
                'percentage': round(percentage, 1),
                'grade': calculate_grade_from_percentage(percentage),
                'status': 'Pass' if percentage >= 40 else 'Fail'
            }
            components_list.append(component_entry)
        
        # IMPROVED: Create subjects with proper pass/fail logic
        subjects = {}
        
        for component in components:
            full_name = component.get('name', 'Unknown')
            component_type = component.get('type', '').lower()
            obtained_marks = component.get('obtained_marks', 0)
            max_marks = component.get('max_marks', 0)
            
            # Enhanced subject name extraction
            subject_name = extract_subject_name(full_name, component_type)
            
            # Initialize subject if not exists
            if subject_name not in subjects:
                subjects[subject_name] = {
                    'subject_name': subject_name,
                    'internal_marks': 0,
                    'external_marks': 0,
                    'internal_max': 0,
                    'external_max': 0,
                    'total_obtained': 0,
                    'total_max': 0,
                    'components': [],
                    'has_internal': False,
                    'has_external': False
                }
            
            # Add component info to subject
            subjects[subject_name]['components'].append({
                'name': full_name,
                'type': component_type,
                'obtained': obtained_marks,
                'max': max_marks
            })
            
            # Categorize marks based on component type
            if is_internal_component(component_type, full_name):
                subjects[subject_name]['internal_marks'] += obtained_marks
                subjects[subject_name]['internal_max'] += max_marks
                subjects[subject_name]['has_internal'] = True
            elif is_external_component(component_type, full_name):
                subjects[subject_name]['external_marks'] += obtained_marks
                subjects[subject_name]['external_max'] += max_marks
                subjects[subject_name]['has_external'] = True
            
            # Add to totals regardless
            subjects[subject_name]['total_obtained'] += obtained_marks
            subjects[subject_name]['total_max'] += max_marks
        
        # Convert subjects to list with proper pass/fail calculation
        subjects_list = []
        overall_subjects_passed = 0
        total_subjects = 0
        
        for subject_name, subject_data in subjects.items():
            total_obtained = subject_data['total_obtained']
            total_max = subject_data['total_max']
            percentage = (total_obtained / total_max * 100) if total_max > 0 else 0
            
            # Subject-wise pass/fail logic
            subject_passed = calculate_subject_pass_status(subject_data, percentage)
            
            if subject_passed:
                overall_subjects_passed += 1
            total_subjects += 1
            
            subject_entry = {
                'subject_name': subject_name,
                'internal_marks': subject_data['internal_marks'],
                'external_marks': subject_data['external_marks'],
                'internal_max': subject_data['internal_max'],
                'external_max': subject_data['external_max'],
                'final_marks': total_obtained,
                'max_marks': total_max,
                'percentage': round(percentage, 1),
                'grade': calculate_grade_from_percentage(percentage),
                'status': 'Pass' if subject_passed else 'Fail',
                'is_passing': subject_passed,
                'component_count': len(subject_data['components']),
                'has_internal': subject_data['has_internal'],
                'has_external': subject_data['has_external'],
                'internal_percentage': round((subject_data['internal_marks'] / subject_data['internal_max'] * 100) if subject_data['internal_max'] > 0 else 0, 1),
                'external_percentage': round((subject_data['external_marks'] / subject_data['external_max'] * 100) if subject_data['external_max'] > 0 else 0, 1)
            }
            subjects_list.append(subject_entry)
        
        # Sort subjects by name for consistent display
        subjects_list.sort(key=lambda x: x['subject_name'])
        
        # Calculate overall result based on subjects
        overall_percentage = sum(subject['percentage'] for subject in subjects_list) / len(subjects_list) if subjects_list else 0
        overall_passed = overall_subjects_passed == total_subjects and total_subjects > 0
        
        # Overall results with proper calculation
        overall = {
            'total_marks': sum(subject['final_marks'] for subject in subjects_list),
            'total_possible': sum(subject['max_marks'] for subject in subjects_list),
            'percentage': round(overall_percentage, 1),
            'grade': calculate_grade_from_percentage(overall_percentage),
            'sgpa': calculate_sgpa_from_subjects(subjects_list),
            'is_passing': overall_passed,
            'subjects_passed': overall_subjects_passed,
            'total_subjects': total_subjects,
            'calculation_method': 'Subject-wise Calculation'
        }
        
        # Add performance analysis
        performance_analysis = get_performance_analysis_subjects(subjects_list, components_list)
        
        results = {
            'student': student,
            'components': components_list,
            'subjects': subjects_list,
            'overall': overall,
            'performance_analysis': performance_analysis,
            'launch_info': {
                'launch_name': result_row['launch_name'],
                'launch_date': result_row['launch_date']
            }
        }
        
        cursor.close()
        connection.close()
        
        logging.info(f"Successfully retrieved results for student {student_id}")
        logging.info(f"Subjects: {total_subjects}, Passed: {overall_subjects_passed}")
        for subject in subjects_list:
            logging.info(f"Subject: {subject['subject_name']} - {subject['percentage']}% - {subject['status']}")
        
        return results
    
    except Exception as e:
        logging.error(f"Error fetching student results: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def calculate_grade_from_percentage(percentage: float) -> str:
    """Calculate grade based on percentage"""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B+'
    elif percentage >= 60:
        return 'B'
    elif percentage >= 50:
        return 'C+'
    elif percentage >= 40:
        return 'C'
    else:
        return 'F'

def get_active_launches() -> List[Dict]:
    """Get all active result launches (for admin/debugging)"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT lr.id, lr.launch_name, lr.launch_date, lr.status,
               s.section_name, lr.email_sent,
               COUNT(swr.id) as student_count
        FROM launched_results lr
        JOIN sections s ON lr.section_id = s.id
        LEFT JOIN student_web_results swr ON lr.id = swr.launch_id
        WHERE lr.status = 'active'
        GROUP BY lr.id, lr.launch_name, lr.launch_date, lr.status, s.section_name, lr.email_sent
        ORDER BY lr.launch_date DESC
        """
        
        cursor.execute(query)
        launches = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for launch in launches:
            if launch['launch_date']:
                launch['launch_date'] = launch['launch_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        connection.close()
        
        return launches
    
    except Exception as e:
        logging.error(f"Error fetching active launches: {e}")
        return []

def get_database_stats() -> Dict:
    """Get database statistics for debugging"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        stats = {}
        
        # Count tables
        tables = ['students', 'sections', 'launched_results', 'student_web_results']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result = cursor.fetchone()
                stats[f'{table}_count'] = result['count']
            except Exception as e:
                stats[f'{table}_count'] = f"Error: {str(e)}"
        
        # Active launches
        try:
            cursor.execute("SELECT COUNT(*) as count FROM launched_results WHERE status = 'active'")
            result = cursor.fetchone()
            stats['active_launches'] = result['count']
        except Exception as e:
            stats['active_launches'] = f"Error: {str(e)}"
        
        # Students with results
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT swr.student_id) as count 
                FROM student_web_results swr
                JOIN launched_results lr ON swr.launch_id = lr.id
                WHERE lr.status = 'active'
            """)
            result = cursor.fetchone()
            stats['students_with_results'] = result['count']
        except Exception as e:
            stats['students_with_results'] = f"Error: {str(e)}"
        
        cursor.close()
        connection.close()
        
        return stats
    
    except Exception as e:
        logging.error(f"Error getting database stats: {e}")
        return {'error': str(e)}

# Initialize database connection test on import
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing database connection...")
    if test_database_connection():
        print("✅ Database connection successful!")
        stats = get_database_stats()
        print("📊 Database Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    else:
        print("❌ Database connection failed!")