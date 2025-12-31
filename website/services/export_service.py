from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import csv
from io import BytesIO
from datetime import datetime


class ReportExporter:
    """Handle report exports in different formats"""
    
    @staticmethod
    def export_appointments_csv(report_data, start_date, end_date):
        """Export appointments report as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="appointments_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Appointments Report'])
        writer.writerow([f'Period: {start_date} to {end_date}'])
        writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Appointments', report_data['total']])
        writer.writerow([])
        
        # Status Breakdown
        writer.writerow(['Status Breakdown'])
        writer.writerow(['Status', 'Count'])
        for status, count in report_data['status_breakdown'].items():
            writer.writerow([status.title(), count])
        writer.writerow([])
        
        # Top Doctors
        writer.writerow(['Top Doctors by Appointments'])
        writer.writerow(['Doctor Name', 'Appointments'])
        for doctor in report_data['top_doctors']:
            writer.writerow([doctor['name'], doctor['count']])
        writer.writerow([])
        
        # Daily Breakdown
        writer.writerow(['Daily Breakdown'])
        writer.writerow(['Date', 'Appointments'])
        for day in report_data['daily_breakdown']:
            writer.writerow([day['date'], day['count']])
        
        return response
    
    @staticmethod
    def export_appointments_pdf(report_data, start_date, end_date):
        """Export appointments report as PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#214994'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#214994'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        # Title
        elements.append(Paragraph("Appointments Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Report Info
        info_data = [
            ['Report Period:', f'{start_date} to {end_date}'],
            ['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')],
            ['Total Appointments:', str(report_data['total'])]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Status Breakdown
        elements.append(Paragraph("Status Breakdown", heading_style))
        status_data = [['Status', 'Count', 'Percentage']]
        total = report_data['total']
        for status, count in report_data['status_breakdown'].items():
            percentage = f"{(count/total*100):.1f}%" if total > 0 else "0%"
            status_data.append([status.title(), str(count), percentage])
        
        status_table = Table(status_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Top Doctors
        if report_data['top_doctors']:
            elements.append(Paragraph("Top Doctors by Appointments", heading_style))
            doctor_data = [['Rank', 'Doctor Name', 'Appointments']]
            for idx, doctor in enumerate(report_data['top_doctors'], 1):
                doctor_data.append([str(idx), doctor['name'], str(doctor['count'])])
            
            doctor_table = Table(doctor_data, colWidths=[0.8*inch, 3.5*inch, 1.5*inch])
            doctor_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))
            elements.append(doctor_table)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="appointments_report_{start_date}_to_{end_date}.pdf"'
        response.write(pdf)
        
        return response
    
    @staticmethod
    def export_doctors_csv(report_data, start_date, end_date):
        """Export doctors report as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="doctors_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Doctors Performance Report'])
        writer.writerow([f'Period: {start_date} to {end_date}'])
        writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Total Doctors', report_data['total_doctors']])
        writer.writerow([])
        
        # Doctor Statistics
        writer.writerow(['Doctor Performance'])
        writer.writerow(['Doctor Name', 'Specialization', 'Appointments', 'Completed', 'Completion Rate', 'Rating'])
        for doctor in report_data['doctor_stats']:
            writer.writerow([
                doctor['name'],
                doctor['specialization'],
                doctor['appointments'],
                doctor['completed'],
                f"{doctor['completion_rate']}%",
                doctor['rating']
            ])
        
        return response
    
    @staticmethod
    def export_doctors_pdf(report_data, start_date, end_date):
        """Export doctors report as PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#214994'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#214994'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        # Title
        elements.append(Paragraph("Doctors Performance Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Report Info
        info_data = [
            ['Report Period:', f'{start_date} to {end_date}'],
            ['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')],
            ['Total Doctors:', str(report_data['total_doctors'])]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Doctor Statistics
        elements.append(Paragraph("Doctor Performance Statistics", heading_style))
        
        # Split into chunks if too many doctors
        chunk_size = 15
        for i in range(0, len(report_data['doctor_stats']), chunk_size):
            chunk = report_data['doctor_stats'][i:i+chunk_size]
            
            doctor_data = [['Doctor', 'Specialization', 'Appts', 'Completed', 'Rate', 'Rating']]
            for doctor in chunk:
                doctor_data.append([
                    Paragraph(doctor['name'], styles['Normal']),
                    doctor['specialization'],
                    str(doctor['appointments']),
                    str(doctor['completed']),
                    f"{doctor['completion_rate']}%",
                    f"⭐ {doctor['rating']}"
                ])
            
            doctor_table = Table(doctor_data, colWidths=[1.8*inch, 1.3*inch, 0.6*inch, 0.8*inch, 0.7*inch, 0.8*inch])
            doctor_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))
            elements.append(doctor_table)
            
            if i + chunk_size < len(report_data['doctor_stats']):
                elements.append(PageBreak())
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="doctors_report_{start_date}_to_{end_date}.pdf"'
        response.write(pdf)
        
        return response
    
    @staticmethod
    def export_patients_csv(report_data, start_date, end_date):
        """Export patients report as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="patients_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Patients Statistics Report'])
        writer.writerow([f'Period: {start_date} to {end_date}'])
        writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Patients', report_data['total_patients']])
        writer.writerow(['Total Dependents', report_data['total_dependents']])
        writer.writerow(['New Patients (Period)', report_data['new_patients']])
        writer.writerow([])
        
        # Age Distribution
        writer.writerow(['Age Distribution'])
        writer.writerow(['Age Group', 'Count'])
        writer.writerow(['0-18', report_data['age_distribution']['age_0_18']])
        writer.writerow(['19-35', report_data['age_distribution']['age_19_35']])
        writer.writerow(['36-50', report_data['age_distribution']['age_36_50']])
        writer.writerow(['51-65', report_data['age_distribution']['age_51_65']])
        writer.writerow(['65+', report_data['age_distribution']['age_65_plus']])
        writer.writerow([])
        
        # Gender Distribution
        writer.writerow(['Gender Distribution'])
        writer.writerow(['Gender', 'Count'])
        writer.writerow(['Male', report_data['gender_distribution']['male']])
        writer.writerow(['Female', report_data['gender_distribution']['female']])
        
        return response
    
    @staticmethod
    def export_patients_pdf(report_data, start_date, end_date):
        """Export patients report as PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#214994'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#214994'),
            spaceAfter=10,
            spaceBefore=10
        )
        
        # Title
        elements.append(Paragraph("Patients Statistics Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Report Info
        info_data = [
            ['Report Period:', f'{start_date} to {end_date}'],
            ['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')],
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary Statistics
        elements.append(Paragraph("Summary Statistics", heading_style))
        summary_data = [
            ['Metric', 'Count'],
            ['Total Patients', str(report_data['total_patients'])],
            ['Total Dependents', str(report_data['total_dependents'])],
            ['New Patients (Period)', str(report_data['new_patients'])]
        ]
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Age Distribution
        elements.append(Paragraph("Age Distribution", heading_style))
        age_data = [
            ['Age Group', 'Count', 'Percentage'],
            ['0-18', str(report_data['age_distribution']['age_0_18']), 
             f"{(report_data['age_distribution']['age_0_18']/report_data['total_patients']*100):.1f}%" if report_data['total_patients'] > 0 else "0%"],
            ['19-35', str(report_data['age_distribution']['age_19_35']),
             f"{(report_data['age_distribution']['age_19_35']/report_data['total_patients']*100):.1f}%" if report_data['total_patients'] > 0 else "0%"],
            ['36-50', str(report_data['age_distribution']['age_36_50']),
             f"{(report_data['age_distribution']['age_36_50']/report_data['total_patients']*100):.1f}%" if report_data['total_patients'] > 0 else "0%"],
            ['51-65', str(report_data['age_distribution']['age_51_65']),
             f"{(report_data['age_distribution']['age_51_65']/report_data['total_patients']*100):.1f}%" if report_data['total_patients'] > 0 else "0%"],
            ['65+', str(report_data['age_distribution']['age_65_plus']),
             f"{(report_data['age_distribution']['age_65_plus']/report_data['total_patients']*100):.1f}%" if report_data['total_patients'] > 0 else "0%"]
        ]
        age_table = Table(age_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        elements.append(age_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Gender Distribution
        elements.append(Paragraph("Gender Distribution", heading_style))
        gender_data = [
            ['Gender', 'Count', 'Percentage'],
            ['Male', str(report_data['gender_distribution']['male']),
             f"{(report_data['gender_distribution']['male']/(report_data['total_patients']+report_data['total_dependents'])*100):.1f}%"],
            ['Female', str(report_data['gender_distribution']['female']),
             f"{(report_data['gender_distribution']['female']/(report_data['total_patients']+report_data['total_dependents'])*100):.1f}%"]
        ]
        gender_table = Table(gender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#214994')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        elements.append(gender_table)
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="patients_report_{start_date}_to_{end_date}.pdf"'
        response.write(pdf)
        
        return response