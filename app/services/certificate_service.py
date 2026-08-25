from fpdf import FPDF

TEMPLATE = "app/static/certificate_template.png"

def render_certificate_pdf(name, course_title, score, code, issued_date):
    pdf = FPDF(orientation="L", unit="mm", format="A4")  # 297 x 210 mm
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.image(TEMPLATE, x=0, y=0, w=297, h=210)

    pdf.set_text_color(27, 36, 48)  # your ink navy

    pdf.set_font("Helvetica", "B", 26)
    pdf.set_xy(0, 85)
    pdf.cell(297, 12, name, align="C")

    pdf.set_font("Helvetica", "", 13)
    pdf.set_xy(0, 105)
    pdf.cell(297, 8, f"for successfully completing {course_title}", align="C")

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(0, 118)
    pdf.cell(297, 8, f"Score: {score}%", align="C")

    pdf.set_font("Courier", "", 9)  # mono so the code looks official
    pdf.set_xy(0, 185)
    pdf.cell(297, 6, f"Verification code: {code}", align="C")

    return bytes(pdf.output())