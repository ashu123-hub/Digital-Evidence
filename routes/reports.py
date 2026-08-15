from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from database import get_db
from routes.auth import login_required, role_required
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                  TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from config import Config
import os
import uuid

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def list_reports():
    db = get_db()
    cases = list(db.cases.find().sort('created_at', -1))
    for c in cases:
        c['_id'] = str(c['_id'])
        c['evidence_count'] = db.evidence.count_documents({'case_id': c['case_id']})
    return render_template('reports.html', cases=cases)

@reports_bp.route('/reports/generate/<case_id>')
@login_required
def generate_report(case_id):
    db = get_db()
    case = db.cases.find_one({'case_id': case_id})
    if not case:
        flash('Case not found.', 'danger')
        return redirect(url_for('reports.list_reports'))

    evidence_list = list(db.evidence.find({'case_id': case_id}).sort('uploaded_at', 1))
    filename = f"DEMS_Report_{case_id}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(Config.REPORTS_FOLDER, filename)

    _generate_pdf_report(filepath, case, evidence_list, db)

    db.audit_logs.insert_one({
        'user_id': session['user_id'],
        'user_name': session['user_name'],
        'evidence_id': None,
        'action': 'REPORT_GENERATED',
        'ip_address': request.remote_addr,
        'timestamp': datetime.utcnow(),
        'status': 'SUCCESS',
        'details': f"Report generated for case {case_id}"
    })

    return send_file(filepath, as_attachment=True, download_name=filename)

def _generate_pdf_report(filepath, case, evidence_list, db):
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=18, textColor=colors.HexColor('#1a1a2e'),
                                  spaceAfter=6, alignment=TA_CENTER)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                fontSize=11, textColor=colors.HexColor('#16213e'),
                                spaceAfter=4, alignment=TA_CENTER)
    label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.grey)
    value_style = ParagraphStyle('Value', parent=styles['Normal'],
                                  fontSize=10, textColor=colors.black, spaceAfter=3)

    story.append(Paragraph("DIGITAL EVIDENCE MANAGEMENT SYSTEM", title_style))
    story.append(Paragraph("Forensic Evidence Report", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0f3460')))
    story.append(Spacer(1, 12))

    # Case Info
    story.append(Paragraph("CASE INFORMATION", ParagraphStyle('SectionHeader',
        parent=styles['Heading2'], textColor=colors.HexColor('#0f3460'), fontSize=13, spaceAfter=8)))

    case_data = [
        ['Case ID:', case.get('case_id', '-'), 'Case Number:', case.get('case_number', '-')],
        ['Case Title:', case.get('case_title', '-'), 'Crime Type:', case.get('crime_type', '-')],
        ['Investigator:', case.get('investigator_name', '-'), 'Status:', case.get('status', '-').upper()],
        ['Created At:', str(case.get('created_at', '-'))[:19], '', ''],
    ]
    case_table = Table(case_data, colWidths=[1.3*inch, 2.5*inch, 1.3*inch, 2.1*inch])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#e8eaf6')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(case_table)
    story.append(Spacer(1, 16))

    if case.get('description'):
        story.append(Paragraph("Description:", ParagraphStyle('FieldLabel', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#0f3460'), fontName='Helvetica-Bold')))
        story.append(Paragraph(case['description'], value_style))
        story.append(Spacer(1, 12))

    # Evidence Summary
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0f3460')))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"EVIDENCE SUMMARY ({len(evidence_list)} item(s))",
                            ParagraphStyle('SectionHeader2', parent=styles['Heading2'],
                                           textColor=colors.HexColor('#0f3460'), fontSize=13, spaceAfter=8)))

    if evidence_list:
        ev_header = ['#', 'Evidence ID', 'File Name', 'Type', 'Status', 'Uploaded At']
        ev_rows = [ev_header]
        for i, ev in enumerate(evidence_list, 1):
            ev_rows.append([
                str(i),
                ev.get('evidence_id', '-'),
                ev.get('file_name', '-')[:30],
                ev.get('file_type', '-'),
                ev.get('status', '-').upper(),
                str(ev.get('uploaded_at', '-'))[:16]
            ])
        ev_table = Table(ev_rows, colWidths=[0.4*inch, 1.2*inch, 2.1*inch, 0.8*inch, 1.1*inch, 1.4*inch])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8eaf6')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph("No evidence items found for this case.", value_style))

    story.append(Spacer(1, 16))

    # Evidence Details with Chain of Custody
    for ev in evidence_list:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Evidence: {ev.get('evidence_id')} — {ev.get('file_name')}",
                                ParagraphStyle('EvHeader', parent=styles['Heading3'],
                                               textColor=colors.HexColor('#16213e'), fontSize=11, spaceAfter=6)))

        detail_data = [
            ['SHA-256 Hash:', ev.get('sha256_hash', '-')],
            ['File Type:', f"{ev.get('file_type', '-')} | Size: {ev.get('file_size', 0)} bytes"],
            ['Encrypted:', 'Yes (AES-256)' if ev.get('encrypted') else 'No'],
            ['Uploaded By:', f"{ev.get('uploaded_by_name', '-')} at {str(ev.get('uploaded_at', '-'))[:19]}"],
            ['Status:', ev.get('status', '-').upper()],
            ['Remarks:', ev.get('remarks', 'None')],
        ]
        detail_table = Table(detail_data, colWidths=[1.5*inch, 5.7*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(detail_table)

        # Chain of Custody for this evidence
        custody_chain = list(db.chain_of_custody.find(
            {'evidence_id': ev['evidence_id']}).sort('timestamp', 1))
        if custody_chain:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Chain of Custody:", ParagraphStyle('CocLabel', parent=styles['Normal'],
                fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#0f3460'))))
            coc_header = ['#', 'Action', 'User', 'Timestamp', 'Record Hash (first 24 chars)']
            coc_rows = [coc_header]
            for j, c in enumerate(custody_chain, 1):
                coc_rows.append([
                    str(j),
                    c.get('action', '-'),
                    c.get('user_name', '-'),
                    str(c.get('timestamp', '-'))[:16],
                    c.get('record_hash', '-')[:24] + '...'
                ])
            coc_table = Table(coc_rows, colWidths=[0.3*inch, 1.2*inch, 1.3*inch, 1.5*inch, 2.9*inch])
            coc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f8')]),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(coc_table)
        story.append(Spacer(1, 12))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0f3460')))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"Digital Evidence Management System | CONFIDENTIAL",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
