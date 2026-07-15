from whiteneuron.base.utils import base_badge_callback
from .models import ExcelFile, PDFFile, HTMLFile

def excelfile_badge_callback(request):
    return base_badge_callback(request, ExcelFile)

def pdffile_badge_callback(request):
    return base_badge_callback(request, PDFFile)

def htmlfile_badge_callback(request):
    return base_badge_callback(request, HTMLFile)
