from nicegui import ui
from datetime import date, datetime
import json
import os
import csv

class summary:
  def __init__(self):
    self.log_options = []
    self.log_count = 0
    
    self.rows = []
    self.columns = [
      {'name': 'part', 'label': 'Part', 'field': 'part', 'required': True, 'align': 'left'},
      {'name': 'standard', 'label': 'Standard', 'field': 'standard', 'required': True, 'align': 'right'},
      {'name': 'tolerance', 'label': 'Tolerance', 'field': 'tolerance', 'required': True, 'align': 'right'},
      {'name': 'unit', 'label': 'Unit', 'field': 'unit', 'required': True, 'align': 'center'},
      {'name': 'ok', 'label': 'OK', 'field': 'ok', 'required': True, 'align': 'right'},
      {'name': 'ng', 'label': 'NG', 'field': 'ng', 'required': True, 'align': 'right'},
    ]

    self.input_date = None
    self.menu = None
    self.date = None
    self.select_log = None
    self.label_log_count = None
    self.table_log = None
    self.button_export = None

    self.get_logs()
    
    ui.label('Summary').classes('text-h3')

    with ui.row(align_items='end').classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-4 q-pr-md').style('row-gap: 0'):
        self.label_log_count = ui.label(f'Found {self.log_count} logs').classes('text-h6 q-mt-md')

        with ui.input('Date Filter').props('readonly').classes('text-h6') as self.input_date:
          with ui.menu().props('no-parent-event') as self.menu:
            with ui.date(on_change=self.get_logs_render).props('range') as self.date:
              with ui.row().classes('justify-end'):
                ui.button('Close', on_click=self.menu.close).props('flat')
          with self.input_date.add_slot('append'):
            ui.icon('highlight_off').on('click', self.clear_input).classes('cursor-pointer q-pr-sm')
            ui.icon('edit_calendar').on('click', self.menu.open).classes('cursor-pointer')

      with ui.column(align_items='stretch').classes('col-4 q-pl-md q-pr-md').style('row-gap: 0'):
        self.select_log = ui.select(
          label='Select Log',
          options=self.log_options,
          on_change=self.select_log_on_change
        ).classes('text-h6')
        
      with ui.column(align_items='stretch').classes('col-2 q-px-md').style('row-gap: 0'):
        with ui.button(on_click=lambda: self.export(self.log_options)).props('square unelevated align=left').classes('q-py-md text-bold'):
          ui.icon('downloading', size='sm')
          ui.label('Export All').classes('q-ml-sm')

      with ui.column(align_items='stretch').classes('col-2 q-pl-md').style('row-gap: 0'):
        with ui.button(on_click=lambda: self.export([self.select_log.value])).props('square unelevated align=left disable').classes('q-py-md text-bold') as self.button_export:
            ui.icon('arrow_circle_down', size='sm')
            ui.label('Export').classes('q-ml-sm')
        

    with ui.row().classes('full-width').style('column-gap: 0'):
      with ui.column(align_items='stretch').classes('col-12').style('row-gap: 0'):
        self.table_log = ui.table(rows=self.rows, columns=self.columns)

  def get_logs(self):
    self.log_options = []
    self.log_count = 0

    if os.path.exists("logs"):
      for filename in os.listdir("logs"):
        if filename.startswith("log-") and filename.endswith(".json"):
          self.log_options.append(filename[4:-5])

      self.log_options.sort(reverse=True)

      if (self.date is not None and self.date.value is not None and self.date.value != ''):
        self.log_options = [log for log in self.log_options if datetime.strptime(log, '%Y-%m-%d').date() >= datetime.strptime(self.date.value['from'], '%Y-%m-%d').date()]
        self.log_options = [log for log in self.log_options if datetime.strptime(log, '%Y-%m-%d').date() <= datetime.strptime(self.date.value['to'], '%Y-%m-%d').date()]
        # self.input_date.set_value(f'{self.input_date.value["from"]} to {self.input_date.value["to"]}')
      
      self.log_count = len(self.log_options)

  def get_logs_render(self):
    self.menu.close()
    self.get_logs()

    if (self.date is not None and self.date.value is not None and self.date.value != ''):
      self.input_date.set_value(f'{self.date.value["from"]} to {self.date.value["to"]}')

    if (self.select_log is not None):
      self.select_log.set_options(self.log_options)

    if (self.label_log_count is not None):
      self.label_log_count.set_text(f'Found {self.log_count} logs')

  def clear_input(self):
    self.input_date.set_value(None)
    self.date.set_value(None)
    # self.get_logs()

    # if (self.select_log is not None):
    #   self.select_log.set_options(self.log_options)

    # if (self.label_log_count is not None):
    #   self.label_log_count.set_text(f'Found {self.log_count} logs')

  def select_log_on_change(self):
    log_file_path = os.path.join("logs", f'log-{self.select_log.value}.json')
    
    if not os.path.isfile(log_file_path):
      print(f"Log file {log_file_path} does not exist.")
      return
    
    with open(log_file_path, 'r') as log_file:
      data = json.load(log_file)
      grouped_data = {}
      for entry in data:
        # Create a unique key using part, standard, and hysteresis
        key = (entry['part'], entry['std'], entry['hysteresis'])
        status = entry['status']

        # Initialize the group if it doesn't exist
        if key not in grouped_data:
          grouped_data[key] = {
            'part': entry['part'],
            'standard': entry['std'],
            'unit': entry['unit'],
            'tolerance': entry['hysteresis'],
            'ok': 0,
            'ng': 0
          }
        
        # Increment the appropriate counter
        if status == "OK":
          grouped_data[key]['ok'] += 1
        else:
          grouped_data[key]['ng'] += 1

      # Convert grouped data to rows
      self.rows = []
      for values in grouped_data.values():
        self.rows.append({
          'part': values['part'],
          'standard': values['standard'],
          'tolerance': f"{values['tolerance']:.2f}",
          'unit': values['unit'],
          'ok': values['ok'],
          'ng': values['ng'],
        })

      self.table_log.rows = self.rows
  
      self.button_export.props(remove='disable')

  def export(self, filenames):
    export_data = []
    export_data.append((
      'Date',
      'Time',
      'Part',
      'Standard',
      'Unit',
      'Tolerance',
      'Measured',
      'Status'
    ))

    if not filenames:
      ui.notify(
        'No log provided for export',
        color='negative'
      )
      return

    for filename in filenames:
      log_file_path = os.path.join("logs", f'log-{filename}.json')
      if not os.path.isfile(log_file_path):
        print(f"Log file {log_file_path} does not exist.")
        return
      
      with open(log_file_path, 'r') as log_file:
        data = json.load(log_file)

        for entry in data:
          export_data.append((
            entry['date'],
            entry['time'],
            entry['part'],
            entry['std'],
            entry['unit'],
            entry['measured'],
            f"{entry['hysteresis']:.2f}",
            entry['status']
          ))

    # Define the CSV file path with today's date
    export_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    csv_file_path = os.path.join("exports", export_filename)

    # Ensure the exports directory exists
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    with open(csv_file_path, mode='w', newline='') as csv_file:
      writer = csv.writer(csv_file)
      writer.writerows(export_data)

      ui.notify(
        f'Log file exported successfully to exports/{export_filename}',
        color='green'
      )



