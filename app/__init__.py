from flask import Flask, render_template, request, redirect, flash, url_for, abort, jsonify, send_file
from celery import Celery
from datetime import timedelta, datetime
import csv
import os
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
import shutil
from .image_processor import app_settings as ap
import time
import pandas as pd
import numpy as np
import math
from celery.utils.log import get_task_logger
import random


dir_path = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = dir_path + '/static/media/'
TASK_ID_FILE_NAME = "tasks.csv"
TASK_CSV = "tasks.csv"
SUCCESS = "SUCCESS"


def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['CELERY_BACKEND'] = "redis://localhost:6379/0"
app.config['CELERY_BROKER_URL'] = "redis://localhost:6379/0"
app.config['CELERY_TIMEZONE'] = 'UTC'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

celery_app = make_celery(app)
celery_logger = get_task_logger(__name__)

@app.route("/.well-known/pki-validation/A634305538F0EED256504DD59E469F9C.txt")
def ssl():
    return send_file("static/A634305538F0EED256504DD59E469F9C.txt")


@app.route('/allfolders')
def allfolder_route():
    directory_contents = os.listdir(UPLOAD_FOLDER)
    f_list = []
    for item in directory_contents:
        if os.path.isdir(item):
            f_list.extend(item)
    return jsonify(directory_contents)


@app.route('/deletefolder/<string:folder_id>')
def delete_route(folder_id):
    check_dir = UPLOAD_FOLDER + folder_id
    if os.path.exists(check_dir):
        try:
            shutil.rmtree(check_dir)
            return f'"{folder_id}" deleted successfully'
        except OSError as e:
            return "Error: %s : %s" % (dir_path, e.strerror)
    return jsonify({
            "response": f'Folder name with following name "{folder_id}" not found',
            "status": "404 Page Not Found"
        }), 404


@app.route('/taskstatus/<folder_id>')
def get_task_status(folder_id):
    check_dir = UPLOAD_FOLDER + folder_id
    if os.path.exists(check_dir):
        df = pd.read_csv(check_dir+"/"+TASK_ID_FILE_NAME)
        return df.to_html()
    return jsonify({
            "response": f'Folder name with following name "{folder_id}" not found',
            "status": "404 Page Not Found"
        }), 404


@app.route('/getimages/<folder_id>')
def getimages(folder_id):
    check_dir = UPLOAD_FOLDER + folder_id
    if os.path.exists(check_dir):
        images_list = [
            request.url_root+f"static/media/{folder_id}/"+i for i in os.listdir(check_dir)]
        return jsonify(images_list)
    return jsonify({
            "response": f'Folder name with following name "{folder_id}" not found',
            "status": "404 Page Not Found"
        }), 404


def get_media_folder():
    return UPLOAD_FOLDER


def devide_task(csv_path, current_folder_path):
    df = pd.DataFrame(columns=["task_id", "from", "to", "status"])
    num_lines = 0
    with open(csv_path, "r") as file:
        num_lines = sum(1 for line in file)
    num_lines -= 1
    spliter = ap['task_spliter']
    total_tasks = int(num_lines/spliter)
    i = 0
    for i in range(total_tasks):
        from_l, to = i*spliter, spliter*(i+1)
        task_celery = csv_file_reader.delay(
            csv_path, from_l, to, i, current_folder_path+TASK_ID_FILE_NAME)
        df.loc[i] = [task_celery.task_id, from_l, to, "Pending"]
    if num_lines % spliter != 0:
        if i > 0:
            i += 1
        from_l, to = total_tasks*spliter, total_tasks*spliter + num_lines % spliter
        task_celery = csv_file_reader.delay(
            csv_path, from_l, to, i, current_folder_path+TASK_ID_FILE_NAME)
        df.loc[i] = [task_celery.task_id, from_l, to, "Pending"]
    df.to_csv(current_folder_path+TASK_ID_FILE_NAME, index=False)
    del df


@app.route('/uploader', methods=['GET', 'POST'])
def get_file():
    flash(u'Folder name already exist please choose other name.', 'error')
    if request.method == 'POST':
        folder_id = request.form['folder_id']
        save_dir = UPLOAD_FOLDER+folder_id
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            f = request.files['file']
            csv_path = save_dir + "/" + f.filename
            f.save(csv_path)
            df = pd.read_csv(csv_path)
            df["position"] = np.random.choice( request.form.getlist('boxposition'), len(df))

            # fontboxcolor
            df["font_box"] = np.random.choice( request.form.getlist('fontboxcolor'), len(df))
            new_both_font_box = df["font_box"].str.split("-", n = 1, expand = True) 

            df["text_font_color"] = new_both_font_box[0]
            df["url_font_color"] = new_both_font_box[0]

            df["text_rectangle_color"] = new_both_font_box[1]
            df["url_rectangle_color"] = new_both_font_box[1]

            df['text_font_style'] = np.random.choice( request.form.getlist('fontstyle'), len(df))
            df['url_font_style'] = np.random.choice( request.form.getlist('fontstyle'), len(df))
            df["text_font_size"] = 0.200
            df["url_font_size"] = 0.036
            df["box_type"] = np.random.choice( request.form.getlist('boxtype'), len(df))
            df["border_width"] = 0
            df["border_color"] = request.form['polygonebordercolor']
            df['rectangle_width'] = request.form['rectanglewidth']
            df.loc[df['box_type'] == 'polygon', 'rectangle_width'] = request.form['polygonwidth']
            df.loc[df['box_type'] == 'polygon', 'border_width'] = request.form['polygoneborderpx']
            df['url_rectangle_width'] = 100
            df.to_csv(csv_path, index=False)
            del df
            devide_task(csv_path, save_dir+"/")
            flash(u'File has been uploaded successfully!', 'success')
        return redirect(url_for('upload_file'))


@celery_app.task()
def csv_file_reader(file_name, from_index, to_index, task_index, report_to_file):
    result = "ERROR"
    df = pd.read_csv(file_name)
    celery_logger.info(f"From: {from_index} to To: {to_index}")
    for i, row in df[from_index:to_index].iterrows():
        result = load_update_img(row['url'], row['text'], "", row['position'], row['site'], 
                                row['text_font_color'], row['url_font_color'], row['text_rectangle_color'],
                                row['url_rectangle_color'], row['text_font_size'], row['url_font_size'],
                                row['box_type'], row['border_width'], row['border_color'], row['rectangle_width'],
                                row['url_rectangle_width'], row['text_font_style'], row['url_font_style'],
                                 os.path.dirname(file_name))
    del df
    df = pd.read_csv(report_to_file)
    df.loc[task_index, "status"] = SUCCESS
    df.to_csv(report_to_file, index=False)
    del df
    return result


def load_update_img(url, text, name, font_position, site_link, text_font_color, url_font_color,
                    text_rectangle_color, url_rectangle_color, text_font_size, url_font_size,
                    box_type, border_width, border_color, rectangle_width, url_rectangle_width,
                    text_font_style, url_font_style,
                    save_folder):
    _, file_extension = os.path.splitext(url)
    if file_extension != "":
        try:
            response = requests.get(url)
            url_byte = BytesIO(response.content)
            text_font_style = dir_path + "/" + text_font_style
            url_font_style = dir_path + "/" + url_font_style
            text_rectangle_color_l = [rgba for rgba in text_rectangle_color[5:-1].replace(" ", "").split(",")]
            text_rectangle_color = tuple(int(trc) for trc in text_rectangle_color_l[0:3])
            url_rectangle_color_l = [rgba for rgba in url_rectangle_color[5:-1].replace(" ", "").split(",")]
            url_rectangle_color = tuple(int(urc) for urc in  url_rectangle_color_l[0:3])
            text_rectangle_opacity = float(text_rectangle_color_l[3])
            url_rectangle_opacity = float(url_rectangle_color_l[3])
            print(text_rectangle_color_l)
            # ----------------- rgba({text_font_color}) 
            text_font_color = text_font_color
            url_font_color = url_font_color
            text_font_size = text_font_size
            url_font_size = url_font_size
            margin_lr = ap["margin_lr"]
            image_opacity = ap["image_opacity"]
            bmt = ap["bottom_margin_text"]
            url_link = site_link
            output_name = save_folder+"/" + str(int(datetime.now().timestamp())+random.randint(0,9999)) + file_extension +"/" text
            # its the image aplha not the rectangle color--os.path.basename(url)

            if font_position.lower() == "bottom" and box_type == "rectangle":
                font_position = 1
                url_position = -1
            elif font_position.lower() == "middle" or font_position == "0":
                font_position = 0
                url_position = 1
            else:
                font_position = -1
                url_position = 1

            image_out = draw_text(url_byte, text, text_font_style, rectangle_width,
                                  percent_margin=margin_lr, font_size_scale=text_font_size,
                                  output_name=output_name, position=font_position, back_op=image_opacity, rect_op=text_rectangle_opacity,
                                  font_color=text_font_color, rectangle_color=text_rectangle_color,
                                  draw_url=None, bottom_margin_text=bmt, box_type=box_type,
                                  border=border_width, border_color=border_color)

            image_out = draw_text(image_out, url_link, url_font_style, url_rectangle_width,
                                  percent_margin=margin_lr, font_size_scale=url_font_size,
                                  output_name=output_name, position=url_position, back_op=image_opacity, rect_op=url_rectangle_opacity,
                                  font_color=url_font_color, rectangle_color=url_rectangle_color,
                                  draw_url="Yes", bottom_margin_text=bmt)
            image_out.save(output_name, optimize=True)
            image_out.close()
            url_byte.close()
            return "Task Completed"
        except Exception as e:
            app.logger.info(e)
            return "ERROR"


@app.route('/')
def upload_file():
    data = {}
    data['fontstyles'] = ['segoeui.ttf', 'impact.ttf']
    data['boxtype'] = ['rectangle', 'polygon']
    return render_template("index.html", data=data)


def text_wrap(text, font, max_width):
    lines = []
    # If the width of the text is smaller than image width
    # we don't need to split it, just add it to the lines array
    # and return
    if font.getsize(text)[0] <= max_width:
        lines.append(text)
    else:
        # split the line by spaces to get words
        words = text.split(' ')
        i = 0
        # append every word to a line while its width is shorter than image width
        while i < len(words):
            line = ''
            while i < len(words) and font.getsize(line + words[i])[0] <= max_width:
                line = line + words[i] + " "
                i += 1
            if not line:
                line = words[i]
                i += 1
            # when the line gets longer than the max width do not append the word,
            # add the line to the lines array
            lines.append(line)
    return lines


def background_image_opacity(img, rect_cord, opacity=25, color = (255,255,255), border=None, border_color=None):
    TINT_COLOR = color  # Black
    TRANSPARENCY = opacity  # Degree of transparency, 0-100%
    OPACITY = int(255 * TRANSPARENCY)

    img = img.convert("RGBA")
    overlay = Image.new('RGBA', img.size, TINT_COLOR+(0,))
    draw = ImageDraw.Draw(overlay)  # Create a context for drawing things on it.
    
    if border:
        draw.line(rect_cord, fill=border_color, width=border)
    draw.polygon(rect_cord, fill=TINT_COLOR+(OPACITY,))
    
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB") # Remove alpha for saving in jpg format.


def draw_text(url, text, font_style, rect_percent, font_size_scale, output_name,
              position, percent_margin , back_op, rect_op, font_color, rectangle_color,
              draw_url, bottom_margin_text, box_type='rectanlge', border=None, border_color=None, left_align=False):    
    # open the background file
    if not draw_url:
        img = Image.open(url)
        draw = ImageDraw.Draw(img)
    else:
        img = url
        draw = ImageDraw.Draw(url)
    image_size = img.size 
    # create the ImageFont instance
    font_size = int(img.size[0] * font_size_scale)
    font_file_path = font_style
    font = ImageFont.truetype(font_file_path, size=font_size, encoding="unic")
    text_box_width = int((rect_percent * image_size[0])/100)
    
    # get shorter lines
    margin_cal = int((percent_margin*text_box_width)/100)
    lines = text_wrap(text, font, text_box_width-margin_cal)
    line_height = font.getsize('hg')[0]
    box_height = line_height * (len(lines)) + line_height/bottom_margin_text
    img_center = int(image_size[0]/2)
    box_center = text_box_width/2
    start_position = (img_center-box_center) - margin_cal
    x_start = 0
    y = 0
    if position == -1:
        y = 0
    elif position == 0:
        y = int(image_size[1]/2 - box_height/2)
    else:
        box_height += int(img.size[0] * 0.0)
        y = int(image_size[1] - box_height) - y
    
    x0 = start_position
    y0 = y
    
    x_end = start_position+text_box_width + margin_cal
    y_end = y+box_height
    
    cor = ((x0,y0), (x_end,y0), (x_end, y_end), (x0, y_end), (x0, y0))
    if box_type == 'polygon':
        middle_x = int(x0+ (x_end-x0)/2)
        middle_y = int(y_end+ (y_end-y0)/2)
        cor = ((x0,y0), (x_end,y0), (x_end, y_end), (middle_x,middle_y), (x0, y_end), (x0,y0))
    
    img = background_image_opacity(img, cor, opacity=rect_op, color=rectangle_color, border=border, border_color=border_color)
    draw = ImageDraw.Draw(img)
    
    for line in lines:
        text_center = int(font.getsize(line)[0]/2)
        center_dif = img_center - text_center
        x = x_start + center_dif
        if left_align:
            x = x0 + margin_cal
        # draw the line on the image
        draw.text((x, y), line, fill=font_color, font=font)

        # update the y position so that we can use it for next line
        y = y + line_height
    # save the image
    return img
