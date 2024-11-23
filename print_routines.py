from nicegui import ui
import cups
import json
import os
import time
from datetime import datetime
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from layout import Layout, Size, Padding, Label, Position
from dataclasses import asdict

class PrintRoutines:
  def print_job(part, qty):
    try:
      print_settings_path = os.path.join("settings", 'page.json')
      
      if not os.path.isfile(print_settings_path):
        print(f'Print Settings file {print_settings_path} does not exist.')
        return
      
      with open(print_settings_path, 'r') as print_settings_file:
        data = json.load(print_settings_file)
        size = Size(**data['size'])
        padding = Padding(**data['padding'])
        label = Label(
            part=Position(**data['position']['part']),
            date=Position(**data['position']['date']),
            qty=Position(**data['position']['qty'])
        )
        layout = Layout(size=size, padding=padding, position=label)

      with open('settings/page.json', 'r') as file:
        json_data = json.load(file)

        dt = datetime.now()
        filename = f"{part['name']}-{dt.strftime('%Y%m%d')}-{dt.strftime('%H%M%S')}.pdf"
        file_path = os.path.join('label', filename)

        # font_name = "custom_font"
        # font_path = "fonts/THSarabunNew.ttf"

        # Register the custom font
        # pdfmetrics.registerFont(TTFont(font_name, font_path))

        # Create a canvas object with the specified paper size
        paper_size = (layout.size.w * mm, layout.size.h * mm)
        c = canvas.Canvas(file_path, pagesize=paper_size)

        # Set the font and size
        c.setFontSize(14)

        # Draw the text on the canvas
        # width, height = GlobalConfig.paper_size
        c.drawString((layout.padding.l + layout.position.part.x) * mm, layout.size.h - ((layout.padding.t + layout.position.part.y) * mm), part['name'])
        c.drawString((layout.padding.l + layout.position.date.x) * mm, layout.size.h - ((layout.padding.t + layout.position.date.y) * mm), f"{dt.strftime('%Y-%m-%d')}")
        c.drawString((layout.padding.l + layout.position.qty.x) * mm, layout.size.h - ((layout.padding.t + layout.position.qty.y) * mm), f"{qty}")

        # Save the PDF file
        c.save()

        conn = cups.Connection()
        printer_name = conn.getDefault()
        print_job_id = conn.printFile(printer_name, file_path, "Print Job", {})

        job_attributes = conn.getJobAttributes(print_job_id)
        job_state = job_attributes['job-state']
        PrintRoutines.log_data(part, qty, print_job_id, job_state)

        while True:
          job_attributes = conn.getJobAttributes(print_job_id)
          job_state = job_attributes['job-state']
          # Check if the job is completed or canceled
          if job_state in [cups.IPP_JOB_COMPLETED, cups.IPP_JOB_CANCELED, cups.IPP_JOB_ABORTED]:
            # print(job_state)
            PrintRoutines.update_job_state(print_job_id, job_state)
            break
          elif job_state in [cups.IPP_JOB_PROCESSING, cups.IPP_JOB_HELD, cups.IPP_JOB_PENDING, cups.IPP_JOB_STOPPED]:
            # print(job_state)
            PrintRoutines.update_job_state(print_job_id, job_state)

          # Wait for a short period before checking again
          time.sleep(1)
    except Exception as e:
        print(f"An error occurred during printing: {e}")

    return True
  
  def reprint_job(job_id):
    try:
      conn = cups.Connection()

      job_attributes = conn.getJobAttributes(job_id)
      if not job_attributes:
        print(f"Job ID {job_id} not found.")
        return False

      conn.restartJob(job_id)
      job_attributes = conn.getJobAttributes(job_id)
      job_state = job_attributes['job-state']
      PrintRoutines.update_job_state(job_id, job_state)

      while True:
        job_attributes = conn.getJobAttributes(job_id)
        job_state = job_attributes['job-state']
        # Check if the job is completed or canceled
        if job_state in [cups.IPP_JOB_COMPLETED, cups.IPP_JOB_CANCELED, cups.IPP_JOB_ABORTED]:
          # print(job_state)
          PrintRoutines.update_job_state(job_id, job_state)
          break
        elif job_state in [cups.IPP_JOB_PROCESSING, cups.IPP_JOB_HELD, cups.IPP_JOB_PENDING, cups.IPP_JOB_STOPPED]:
          # print(job_state)
          PrintRoutines.update_job_state(job_id, job_state)

        # Wait for a short period before checking again
        time.sleep(1)
    except Exception as e:
      return f'An error occurred during reprinting: {e}'

    return True
  
  def log_data(part, qty, job_id, job_state):
    # Get the current date in the format yyyy-mm-dd
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    log_filename = f"logs/print-job-{current_date}.json"

    # Check if the logs directory exists, if not, create it
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Check if the log file exists
    if not os.path.isfile(log_filename):
      with open(log_filename, 'w') as log_file:
        json.dump([], log_file)

    log_entry = {
      "date": current_date,
      "time": current_time,
      "part": part['name'],
      "std": part['std'],
      "unit": part['unit'],
      "hysteresis": part['hysteresis'],
      "jobid": job_id,
      "qty": qty,
      "state": job_state
    }

    with open(log_filename, 'r+') as log_file:
      data = json.load(log_file)
      data.append(log_entry)
      log_file.seek(0)
      json.dump(data, log_file, indent=4)

  def update_job_state(job_id, new_job_state):
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"logs/print-job-{current_date}.json"

    if not os.path.isfile(log_filename):
      print(f"Log file {log_filename} does not exist.")
      return False
    
    with open(log_filename, 'r') as log_file:
      data = json.load(log_file)

    job_found = False
    for entry in data:
      if entry['jobid'] == job_id:
        entry['state'] = new_job_state
        job_found = True
        break

    if not job_found:
      print(f"Job ID {job_id} not found in log file.")
      return False
    
    with open(log_filename, 'w') as log_file:
      json.dump(data, log_file, indent=4)

    return True