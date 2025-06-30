import os
import logging
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from flask_cors import CORS
from database import get_student_results, get_sections, verify_student_login, get_active_launches
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-12345")
CORS(app)

# Cache sections to avoid repeated database calls
_cached_sections = None

def generate_captcha():
    """Generate a simple math captcha"""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-'])
    
    if operation == '+':
        answer = num1 + num2
        question = f"{num1} + {num2}"
    else:
        # Make sure we don't get negative results
        if num1 < num2:
            num1, num2 = num2, num1
        answer = num1 - num2
        question = f"{num1} - {num2}"
    
    return question, str(answer)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Single page with section dropdown, login form and results"""
    global _cached_sections
    
    # Generate captcha for each request
    captcha_question, captcha_answer = generate_captcha()
    
    # Use cached sections or load from database
    if _cached_sections is None:
        try:
            _cached_sections = get_sections()
            logging.info(f"Loaded sections from database: {_cached_sections}")
            if not _cached_sections:
                _cached_sections = ["No active results available"]
                logging.warning("No sections found, using default message")
        except Exception as e:
            logging.error(f"Error loading sections: {str(e)}")
            _cached_sections = ["Error loading sections"]
    
    sections = _cached_sections
    logging.info(f"Sections being sent to template: {sections}")
    
    if request.method == 'POST':
        section = request.form.get('section', '').strip()
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        captcha_input = request.form.get('captcha', '').strip()
        captcha_answer_form = request.form.get('captcha_answer', '').strip()
        
        logging.info(f"Form submission - Section: '{section}', Name: '{name}', Roll: '{roll_number}'")
        logging.info(f"Captcha - Input: '{captcha_input}', Expected: '{captcha_answer_form}'")
        
        error_msg = None
        
        # Validate all fields
        if not all([section, name, roll_number, captcha_input]):
            error_msg = "All fields including captcha are required"
            logging.warning("Form validation failed - missing fields")
        elif captcha_input != captcha_answer_form:
            error_msg = "Captcha verification failed. Please try again."
            logging.warning("Captcha verification failed")
        elif section in ["No active results available", "Error loading sections"]:
            error_msg = "No results are currently available. Please contact your administrator."
            logging.warning("No active results available")
        else:
            # Verify student and get results
            try:
                logging.info("Attempting to verify student...")
                student = verify_student_login(section, name, roll_number)
                if student:
                    logging.info(f"Student verified: {student}")
                    student_results = get_student_results(student['id'])
                    if student_results:
                        logging.info("Results found, rendering result page")
                        
                        # Store in session for PDF download
                        session['student_data'] = {
                            'student_name': student['name'],
                            'student_section': section,
                            'student_roll': roll_number,
                            'student_id': student['id']
                        }
                        session['results'] = student_results
                        
                        # Use result.html template
                        return render_template('result.html', results=student_results)
                    else:
                        error_msg = "No results found for your account. Results may not be published yet."
                        logging.warning("No results found for verified student")
                else:
                    error_msg = "Invalid credentials or no results available for this student."
                    logging.warning("Student verification failed")
            except Exception as e:
                logging.error(f"Error during student verification: {str(e)}")
                error_msg = "System error. Please try again later."
        
        # Generate new captcha for error case
        captcha_question, captcha_answer = generate_captcha()
        
        return render_template('index.html', 
                             sections=sections, 
                             error=error_msg,
                             form_data={'section': section, 'name': name, 'roll_number': roll_number},
                             captcha_question=captcha_question,
                             captcha_answer=captcha_answer)
    
    return render_template('index.html', 
                         sections=sections,
                         captcha_question=captcha_question,
                         captcha_answer=captcha_answer)

@app.route('/generate_captcha')
def generate_captcha_endpoint():
    """Generate captcha for AJAX requests"""
    captcha_question, captcha_answer = generate_captcha()
    return jsonify({
        'question': captcha_question,
        'answer': captcha_answer
    })
@app.route('/chart_data/<int:student_id>')
def chart_data(student_id):
    """Get chart data for student - both subject and component data"""
    try:
        # Get results from session if available, otherwise fetch from database
        if 'results' in session and session.get('student_data', {}).get('student_id') == student_id:
            results = session['results']
        else:
            results = get_student_results(student_id)
        
        if results:
            # Prepare both subject and component data
            chart_response = {
                'subjects': {
                    'labels': [subject['subject_name'] for subject in results.get('subjects', [])],
                    'data': [subject['percentage'] for subject in results.get('subjects', [])],
                    'status': [subject['is_passing'] for subject in results.get('subjects', [])]
                },
                'components': {
                    'labels': [comp['component_name'] for comp in results.get('components', [])],
                    'data': [comp['percentage'] for comp in results.get('components', [])],
                    'types': [comp['type'] for comp in results.get('components', [])]
                }
            }
            logging.info(f"Chart data for student {student_id}: subjects={len(chart_response['subjects']['labels'])}, components={len(chart_response['components']['labels'])}")
            return jsonify(chart_response)
        
        logging.warning(f"No chart data found for student {student_id}")
        return jsonify({
            'subjects': {'labels': [], 'data': [], 'status': []}, 
            'components': {'labels': [], 'data': [], 'types': []}
        })
    except Exception as e:
        logging.error(f"Error getting chart data: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'subjects': {'labels': [], 'data': [], 'status': []}, 
            'components': {'labels': [], 'data': [], 'types': []}
        })

@app.route('/download_pdf/<int:student_id>')
def download_pdf(student_id):
    """Generate and download PDF result"""
    try:
        # Get results from session if available, otherwise fetch from database
        if 'results' in session and session.get('student_data', {}).get('student_id') == student_id:
            results = session['results']
            student_data = session['student_data']
        else:
            results = get_student_results(student_id)
            if not results:
                return "Results not found", 404
            student_data = {
                'student_name': results['student']['name'],
                'student_section': results['student']['section'],
                'student_roll': results['student']['roll_number']
            }
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Student Result Report", title_style))
        story.append(Spacer(1, 20))
        
        # Student Info
        student_info = [
            ['Name:', student_data['student_name']],
            ['Section:', student_data['student_section']],
            ['Roll Number:', student_data['student_roll']],
            ['Launch:', results['launch_info']['launch_name']],
            ['Date:', str(results['launch_info']['launch_date']) if results['launch_info']['launch_date'] else 'N/A'],
        ]
        
        student_table = Table(student_info, colWidths=[2*inch, 4*inch])
        student_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(student_table)
        story.append(Spacer(1, 30))
        
        # Component Results Table
        if results.get('components'):
            data = [['Component', 'Type', 'Obtained', 'Max', 'Percentage', 'Grade', 'Status']]
            
            for component in results['components']:
                data.append([
                    component['component_name'],
                                        component['type'],
                    str(component['obtained_marks']),
                    str(component['max_marks']),
                    f"{component['percentage']:.1f}%",
                    component['grade'],
                    component['status']
                ])
            
            # Add overall row
            overall = results['overall']
            data.append([
                'OVERALL',
                '-',
                str(overall['total_marks']),
                str(overall['total_possible']),
                f"{overall['percentage']:.1f}%",
                overall['grade'],
                'Pass' if overall['is_passing'] else 'Fail'
            ])
            
            results_table = Table(data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.6*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(results_table)
        
        # Performance Analysis
        if results.get('performance_analysis'):
            story.append(Spacer(1, 20))
            story.append(Paragraph("Performance Analysis", styles['Heading2']))
            
            analysis = results['performance_analysis']
            analysis_data = [
                ['Performance Level:', analysis['performance_level']],
                ['Average Percentage:', f"{analysis['average_percentage']:.1f}%"],
                ['Strongest Component:', analysis['strongest_component']],
                ['Weakest Component:', analysis['weakest_component']],
                ['Recommendation:', analysis['recommendation']]
            ]
            
            analysis_table = Table(analysis_data, colWidths=[2*inch, 4*inch])
            analysis_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(analysis_table)
        
        doc.build(story)
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=result_{student_data["student_name"].replace(" ", "_")}.pdf'
        
        return response
        
    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        return "Error generating PDF", 500

@app.route('/logout')
def logout():
    """Clear session and redirect to home"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/debug/database')
def debug_database():
    """Debug route to check database status"""
    try:
        from database import get_database_stats, test_database_connection
        
        if not test_database_connection():
            return jsonify({'error': 'Database connection failed'}), 500
        
        stats = get_database_stats()
        sections = get_sections()
        launches = get_active_launches()
        
        return jsonify({
            'database_stats': stats,
            'sections': sections,
            'active_launches': launches,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/launches')
def admin_launches():
    """Debug route to see active launches"""
    try:
        launches = get_active_launches()
        return jsonify(launches)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_cache')
def clear_cache():
    """Clear sections cache"""
    global _cached_sections
    _cached_sections = None
    return jsonify({'message': 'Cache cleared'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)