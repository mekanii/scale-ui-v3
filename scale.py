from nicegui import ui
from datetime import date, datetime
import sys
import json
import os
import asyncio
import threading
import queue
import cups
import pygame
from hx711 import HX711
from print_routines import PrintRoutines

class scale:
  def __init__(self):
    # READ_MODE_INTERRUPT_BASED = "--interrupt-based"
    # READ_MODE_POLLING_BASED = "--polling-based"
    # READ_MODE = READ_MODE_POLLING_BASED

    # if len(sys.argv) > 1 and sys.argv[1] == READ_MODE_POLLING_BASED:
    #   READ_MODE = READ_MODE_POLLING_BASED
    #   print("[INFO] Read mode is 'polling based'.")
    # else:
    #   print("[INFO] Read mode is 'interrupt based'.")

    pygame.mixer.init()


    self.cal_factor = 1
    self.get_cal_factor()

    self.hx = HX711(5, 6)
    self.hx.set_reading_format("MSB", "MSB")

    self.hx.set_reference_unit(self.cal_factor)

    self.hx.reset()

    self.hx.tare(15)
    # print(self.hx.get_reference_unit())

    self.last_part = None
    self.part_options = []
    self.part_count = 0
    self.weight = 0
    self.last_check = 0

    self.count_pack = 0
    self.count_ok = 0
    self.count_ng = 0
    self.count_ok_session = 0

    self.count_try = 0

    self.last_weight = 0.0
    self.stable_weight = 0.0
    self.check_status = 0
    self.stable_readings_count = 0
    self.stable_readings_reaquired = 32

    self.label_count_pack = None
    self.label_count_ok = None
    self.label_count_ng = None
    self.label_check = None

    self.select_part = None

    self.get_parts()
  
    ui.label('Scale').classes('text-h3')
    with ui.row().classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0'):
        self.label_part_count = ui.label(f'Found {self.part_count} parts').classes('text-h6')

        self.select_part = ui.select(
          label='Select Part',
          options=self.part_options,
          on_change=self.select_part_on_change
        ).props(':option-label="(opt) => opt.label.name"').classes('text-h6').style('height: 50px')

        with ui.button(on_click=self.get_parts_render).props('square unelevated align=left').classes('q-py-md q-mt-lg text-bold'):
          ui.icon('cached', size='md')
          ui.label('Reload').classes('text-h6 q-ml-sm')

        with ui.button(on_click=self.tare).props('square unelevated align=left').classes('q-py-md q-mt-lg text-bold'):
          ui.icon('settings_backup_restore', size='md')
          ui.label('Tare').classes('text-h6 q-ml-sm')

      with ui.column().classes('col-8 items-end q-pl-md q-pr-lg'):
        # self.label_selected_part_key = ui.label('').classes('text-h6').style('font-family: "monofonto"; padding-right: 48px;')
        self.label_selected_part_value = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')
        self.label_count_pack = ui.label('').classes('text-h2').style('font-family: "monofonto"')
        self.label_count_ok = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')
        self.label_count_ng = ui.label('').classes('text-h2').style('font-family: "monofonto"; padding-right: 59px;')

    with ui.row().classes('full-width'):
      with ui.column(align_items='stretch').classes('col-12 q-pr-lg').style('row-gap: 0'):
        self.label_weight = ui.label('').classes('text-right').style('font-family: "monofonto"; font-size: 128px')
        
        self.label_check = ui.label('').classes('text-right text-h2 text-positive').style('font-family: "monofonto";')

        # ui.audio(sound_path_ok)
        # ui.audio(sound_path_ng)

  def get_parts(self):
    with open('settings/part.json', 'r') as file:
      self.part_options = json.load(file)
      self.part_count = len(self.part_options)
  
  def get_parts_render(self):
    self.get_parts()
    self.select_part.set_options(self.part_options)
    self.label_part_count.set_text(f'Found {self.part_count} parts')

  def tare(self):
    self.hx.tare()

  async def select_part_on_change(self):
    # self.label_selected_part_key.set_text('Standard Weight ± Tolerance')
    # await self.update_scale()
    if (self.last_part is None):
      await self.update_scale()


  async def update_scale(self):
    while (True):
      if (self.select_part.value is not None):
        if (self.select_part.value['name'] != self.last_part):
          self.last_part = self.select_part.value
          count, self.count_ok, self.count_ng = self.count_log_data(self.select_part.value['name'])

          if (self.select_part.value['pack'] > 0):
            self.count_pack = self.sum_qty_by_part(self.select_part.value)
            self.count_ok_session = (self.count_ok - self.count_pack) % self.select_part.value['pack']
          else:
            self.count_ok_session = self.count_ok

          self.label_selected_part_value.set_text(f'{self.select_part.value["std"]} ± {self.select_part.value["hysteresis"]} {self.select_part.value["unit"]}')
          self.label_count_pack.set_text(f'[{self.count_ok_session} / {self.select_part.value["pack"]}] {self.count_pack} PACK')
          self.label_count_ok.set_text(f'{self.count_ok} OK')
          self.label_count_ng.set_text(f'{self.count_ng} NG')
          
        # get weight
        self.weight, check = await self.get_weight(self.select_part.value['std'], self.select_part.value['unit'], self.select_part.value['hysteresis'])
        # print(f'weight: {self.weight}, check: {check}')

        # if self.select_part.value['unit'] == 'kg':
        #   weight_with_unit = f"{float(format(self.weight, '.2f'))} {self.select_part.value['unit']}"
        # else:
        #   weight_with_unit = f"{int(self.weight)} {self.select_part.value['unit']}"

        if check == 1 and check != self.last_check:
          self.label_check.classes(remove='text-negative', add='text-positive')
          self.label_check.set_text('QTY GOOD')
          await self.play_tone("OK")
          # self.check_label.config(foreground='green')
          # self.check_label.config(text="QTY GOOD")

          self.log_data(self.select_part.value, float(format(self.weight, '.2f')) if self.select_part.value['unit'] == 'kg' else int(self.weight), "OK")
          count, self.count_ok, self.count_ng = self.count_log_data(self.select_part.value['name'])
          
          if (self.select_part.value['pack'] > 0):
            self.count_pack = self.sum_qty_by_part(self.select_part.value)
            self.count_ok_session = (self.count_ok - self.count_pack) % self.select_part.value['pack']
            if self.count_ok_session == 0:
              result_queue = queue.Queue()
              self.count_try = 0
              threading.Thread(target=self.run_print_label, args=(self.select_part.value, self.select_part.value['pack'], result_queue)).start()
              await asyncio.sleep(0.1)
              await self.print_dialog(result_queue)
              # GlobalConfig.print_label(part, self.count_ok_setpoint.get())
          else:
            self.count_ok_session = self.count_ok
          
          self.label_count_pack.set_text(f'[{self.count_ok_session} / {self.select_part.value["pack"]}] {self.count_pack} PACK')
          self.label_count_ok.set_text(f'{self.count_ok} OK')
          # self.label_count_ng.set_text(f'{self.count_ng} NG')

        elif check == 2 and check != self.last_check:
          self.label_check.classes(remove='text-positive', add='text-negative')
          self.label_check.set_text('NOT GOOD')
          await self.play_tone("NG")
          # self.check_label.config(foreground='red')
          # self.check_label.config(text="NOT GOOD")

          self.log_data(self.select_part.value, float(format(self.weight, '.2f')) if self.select_part.value['unit'] == 'kg' else int(self.weight), "NG")
          self.count, self.count_ok, self.count_ng = self.count_log_data(self.select_part.value['name'])

          self.label_count_pack.set_text(f'[{self.count_ok_session} / {self.select_part.value["pack"]}] {self.count_pack} PACK')
          # self.label_count_ok.set_text(f'{self.count_ok} OK')
          self.label_count_ng.set_text(f'{self.count_ng} NG')

        elif check == 0 and check != self.last_check:
          self.label_check.set_text('')
        
        self.last_check = check
        self.label_weight.set_text(f"{float(format(self.weight, '.2f')) if self.select_part.value['unit'] == 'kg' else int(self.weight)} {self.select_part.value['unit']}")
      await asyncio.sleep(0.1)
    
    # print('updating')
    # await self.update_scale()

  def log_data(self, part, scale, status):
    # Get the current date in the format yyyy-mm-dd
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    log_filename = f"logs/log-{current_date}.json"

    if not os.path.exists("logs"):
      os.makedirs("logs")

    if not os.path.isfile(log_filename):
      with open(log_filename, 'w') as file:
        json.dump([], file)

    log_entry = {
      "date": current_date,
      "time": current_time,
      "part": part['name'],
      "std": part['std'],
      "unit": part['unit'],
      "hysteresis": part['hysteresis'],
      "measured": scale,
      "status": status
    }
    
    with open(log_filename, 'r+') as file:
      data = json.load(file)
      data.append(log_entry)
      file.seek(0)
      json.dump(data, file, indent=4)
  
  def count_log_data(self, part_name):
    # Get the current date in the format yyyy-mm-dd
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"logs/log-{current_date}.json"

    # Check if the log file exists
    if not os.path.isfile(log_filename):
      return 0, 0, 0  # Return 0 if the log file does not exist

    # Initialize count
    count = 0
    count_ok = 0
    count_ng = 0

    # Read the log file and count entries for the specified part
    with open(log_filename, 'r') as file:
      data = json.load(file)
      count = sum(1 for entry in data if entry['part'] == part_name)

      count_ok = sum(1 for entry in data if entry['part'] == part_name and entry['status'] == "OK")
      count_ng = sum(1 for entry in data if entry['part'] == part_name and entry['status'] == "NG")

    return count, count_ok, count_ng
  
  def sum_qty_by_part(self, part):
    # Get the current date in the format yyyy-mm-dd
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    print_job_file_path = os.path.join('logs', f'print-job-{current_date}.json')

    if not os.path.isfile(print_job_file_path):
      # ui.notify(
      #   f'Path {print_job_file_path} does not exist.',
      #   type='negative'
      # ) 
      return 0

    # Initialize a variable to store the sum of quantities for the selected part
    total_qty = 0

    # Read the log file and sum quantities for the selected part
    with open(print_job_file_path, 'r') as file:
      data = json.load(file)
      for entry in data:
        if entry['part'] == part['name'] and entry['std'] == part['std'] and entry['hysteresis'] == part['hysteresis']:
          qty = entry.get('qty', 0)
          total_qty += qty
          print(total_qty)

    return total_qty
  
  def get_cal_factor(self):
    calibration_file_path = os.path.join("settings", 'calibration.json')
    
    if not os.path.isfile(calibration_file_path):
      ui.notify(
        f'Path {calibration_file_path} does not exist.',
        type='negative'
      )
      return
    
    with open(calibration_file_path, 'r') as file:
      data = json.load(file)
      self.cal_factor = data['cal_factor']

  def run_print_label(self, part, count_ok_setpoint, result_queue):
    result = PrintRoutines.print_job(part, count_ok_setpoint)
    result_queue.put(result)

  async def print_dialog(self, result_queue):
    with ui.dialog().props('persistent backdrop-filter="invert(70%)"') as dialog, ui.card():
      with ui.row().classes('full-width').style('column-gap: 0'):
        with ui.column(align_items='center').classes('col-12'):
          ui.label('Printing, please wait...').classes('text-h5')
          ui.spinner('box', size='xl')
          button_cancel = ui.button(
            'Cancel',
            color='negative',
            on_click=lambda: self.cancel_print_job(dialog)
          ).classes('invisible')
    dialog.open()
    await self.check_print_label_result(dialog, button_cancel, result_queue)

  async def check_print_label_result(self, dialog, button_cancel, result_queue):
    try:
      # Try to get the result from the queue
      result = result_queue.get_nowait()
      if result == True:
        dialog.close()
      elif isinstance(result, str):
        dialog.close()
        ui.notify(
          result,
          type='negative'
        )
    except queue.Empty:
      # If the queue is empty, check again after a short delay
      current_try = self.count_try
      self.count_try = current_try + 1
      if self.count_try == 200:
        button_cancel.classes(remove='invisible')
      await asyncio.sleep(0.1)
      await self.check_print_label_result(dialog, button_cancel, result_queue)

  def cancel_print_job(self, dialog):
    conn = cups.Connection()
    printer_name = conn.getDefault()
    jobs = conn.getJobs(which_jobs='all', my_jobs=True)

    if not jobs:
      ui.notify(
        'No print jobs found.',
        type='negative'
      )
      return False
    
    last_job_id = max(jobs.keys())
    
    conn.cancelJob(last_job_id)
    ui.notify(
        f'Canceled job ID {last_job_id} for printer {printer_name}.',
        type='negative'
      )
    
    dialog.destroy()

  async def play_tone(self, status):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filename = ""
    if status == "OK":
      filename = "OK.mp3"
    elif status == "NG":
      filename = "NG.mp3"
    sound_path = os.path.join(current_dir, "assets", "tones", filename)

    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.play()

  async def get_weight(self, std, unit, hysteresis):
    # rawBytes = self.hx.getRawBytes()
    # wt = self.hx.rawBytesToWeight(rawBytes)

    wt = self.hx.get_weight(15)
    self.hx.power_down()
    self.hx.power_up()

    # print(f'wt: {wt}')
    
    if (unit == "kg"):
      wt = wt / 1000.0

    if (await self.check_stable_state(wt, std, unit)):
      if (unit == "kg" and wt <= 0.01):
        self.check_status = 0
        self.stable_weight = 0.0
      elif (unit == "gr" and wt <= 2.0):
        self.check_status = 0
        self.stable_weight = 0.0
      elif (wt >= std - hysteresis and wt <= std + hysteresis and self.check_status == 0):
        self.check_status = 1
        self.stable_weight = wt
      elif (self.check_status == 0):
        self.check_status = 2
        self.stable_weight = wt
      
    elif (self.stable_weight != 0.0 and (wt <= self.stable_weight * 0.9 or wt >= self.stable_weight * 1.1)):
      self.check_status = 0
      self.stable_weight = 0.0

    return wt, self.check_status
    
  async def check_stable_state(self, wt, std, unit):
    # diff = std  / ((9600 * 20 / 200) / RS485_BAUD);
    diff = 0.0

    if (unit == "kg"):
      diff = float(std) * 0.1
    else:
      diff = 1.0 if (std == 0) else float(std) * 0.1

    if (wt >= wt - diff and wt <= wt + diff and abs(wt - self.last_weight) <= diff):
      self.stable_readings_count = self.stable_readings_count + 1 if (self.last_weight > diff) else 0
    
    self.last_weight = wt
      
    return (self.stable_readings_count >= self.stable_readings_reaquired)