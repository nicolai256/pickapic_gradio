import gradio as gr
import os
import random
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import base64
import csv
import tqdm
import re
from PIL.PngImagePlugin import PngInfo
Image.MAX_IMAGE_PIXELS = None
####TODO####
#add keyword filter
#add only display similar prompts
#add style filter [anime, landscape, photographic, psychedelic, old art, etc..] (maybe with a thing like what do you want to rate?)
#add checkbox pickapic prefilter for prompt accuracy prediction (70% and up?)
#add checkbox aesthetic rating prefilter for displaying better images by default 
#add folder selection
#add connection to database for getting rating images and sending back ratings
#add rating and raters leaderboard with people's social media links (for motivation)
#add prompt on the top of the image
#add rating good or bad quality images on top of the prompt rating? kind of like midjourney?
#if an image is not rated 😍 add it to a database that asks you what is wrong with the image (bad composition, bad hands, bad anatomy, signature, bad text, etc)
#if an image is not rated 🤮 add it to a database that asks you what is good in the image (interesting composition, good hands, good anatomy, good text, etc)
#add style rating for any ratings rated 😊 and 😍, basically users select which style an image is "anime", "landscape", "psychedelic", "photography","traditional art","characters","typography","architecture","logos", etc

################### PICKAPIC ##################
def add_data_to_csv(best_image, worst_image , prompt, parameters, bothbad, platform):
    if platform == "vlad-automatic":
        parameters = "Steps" + parameters
    # Define the file name and path
    csv_file = "pickapic-v0_1.csv"

    # Check if the CSV file exists
    file_exists = False
    try:
        with open(csv_file, 'r'):
            file_exists = True
    except FileNotFoundError:
        pass

    # Define the field names
    field_names = ["best image", "worst image", "prompt", "parameters", "both bad", "platform"]

    # Open the CSV file in append mode, creating it if necessary
    with open(csv_file, "a", newline="", encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=field_names)

        # Write the header if the file doesn't exist
        if not file_exists:
            writer.writeheader()

        # Write the data row
        writer.writerow({"best image": best_image, "worst image": worst_image, "prompt": prompt, "parameters":parameters, "both bad":bothbad, "platform":platform})

    print("Data added to the CSV file.")

def add_space_before_Negative(sentence):
    # Use regular expressions to add a space before 'person'
    modified_sentence = re.sub(r'(Negative)', r' \1', sentence)
    return modified_sentence
def add_space_before_Steps(sentence):
    # Use regular expressions to add a space before 'person'
    modified_sentence = re.sub(r'(Steps)', r' \1', sentence)
    return modified_sentence

def extract_metadata(image_path, platform):
    print(platform)
    # Load the image

    image = Image.open(image_path)
    
    value = None
    extra_info = None
    if platform == "vlad-automatic":
        try:
            # Extract specific metadata tags
            metadata = {ExifTags.TAGS[key]: value for key, value in image._getexif().items() if key in ExifTags.TAGS}
    
            if metadata:
                for tag, value in metadata.items():
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8")
                            value = value.split("UNICODE", 1)[1].strip()
                            value = value.replace('\x00', '').strip()
                            extra_info = value.split("Steps", 1)[1].strip()
                            prompt = value.split("Steps", 1)[0].strip()
                            print(prompt)
                            print(extra_info)
                        except UnicodeDecodeError:
                            pass
                    #print(f"{value}")
            else:
                print("No metadata found.")
    
        except (IOError, AttributeError):
            print("Error: Unable to open the image.")

    elif platform == "automatic1111":
            #try:
            info = image.info
            info_str = str(info).replace('\\n', '')
            info_str = add_space_before_Negative(info_str)
            info_str = add_space_before_Steps(info_str)

            #get the parameters
            parts1 = info_str.split("Steps:")
            part_0 = parts1[0]
            if len(parts1) > 1:
                part_1 = parts1[1]
                parameters = "Steps: " + part_1
                parameters = parameters.split("'}")
                parameters = parameters[0]
                extra_info = parameters
            
            #get the prompt and negative prompt
            parts2 = part_0.split("Negative prompt:")
            #part_2 = parts2[0]
            #part_3 = parts2[1]
            if len(parts2) > 1:
                prompt = parts2[0] + "\nNegative prompt: " + parts2[1]
            else:
                prompt = parts2[0]
            prompt = prompt.split("{'parameters':")
            if len(prompt) > 1:
                prompt = prompt[1]
            else:
                prompt = prompt[0]
            if prompt.startswith('"') or prompt.startswith(' "'):
                prompt = prompt.replace('"', "", 1)
            if prompt.startswith("'") or prompt.startswith(" '"):
                prompt = prompt.replace("'", "", 1)
            
        #except FileNotFoundError:
            #print("Image not found.")
        #except Exception as e:
            #print("An error occurred while processing the image:", str(e))
    elif platform == "DeepFloyd-IF-webUI":
        try:
            if 'prompt' in image.info:
                prompt = image.info['prompt']
        
            if 'negative_prompt' in image.info:
                negative_prompt = image.info['negative_prompt']

            if 'style_prompt' in image.info:
                style_prompt = image.info['style_prompt']
        
            if 'seed' in image.info:
                seed = int(float(image.info['seed']))
            prompt = prompt + "\n style_prompt: " + style_prompt + "\n negativeprompt: " + negative_prompt 
            extra_info = "Seed: " + str(seed)
        except FileNotFoundError:
            print("Image not found.")
        except Exception as e:
            print("An error occurred while processing the image:", str(e))
    elif platform == 'kandinsky2.1-kubin':
        try:
            
            # Get the metadata from the PNG image
            metadata = image.info
            prompt = metadata.get("prompt")
            png_info_str = str(metadata)
            png_info_str = png_info_str.split(prompt)
            try:
                png_info_str = png_info_str[1]
            except Exception as e:
                png_info_str = png_info_str
            if "," in png_info_str:
                # Remove the first comma and everything before it
                before_comma, after_comma = png_info_str.split(",", 1)
                extra_info = after_comma.split("}")[0]
            else: 
                extra_info = "No"
                    
        except FileNotFoundError:
            print("Image not found.")
        except Exception as e:
            print("An error occurred while processing the image:", str(e))
    elif platform == "invokeai":
        try:
            
            info = str(image.info)
            info = info.split("-s")
            prompt = info[0]
            prompt = prompt.split("{'Dream': '")
            prompt = str(prompt[1])
            prompt = prompt.replace('"', '')
            prompt = prompt.replace('[', ' \nnegative prompt: ')
            prompt = prompt.replace(']', '')
            extra_info = "-s" + info[1]
                
        except FileNotFoundError:
            print("Image not found.")
        except Exception as e:
            print("An error occurred while processing the image:", str(e))

    return prompt, extra_info


def image_pair_generator(folder_path, platform):
    #image_list = os.listdir(folder_path)
    if platform == "vlad-automatic":
        image_list = [filename for filename in os.listdir(folder_path) if filename.lower().endswith(".jpg")]
    else:
        image_list = [filename for filename in os.listdir(folder_path) if filename.lower().endswith(".png")]
    random.shuffle(image_list) 
    matched_pairs = set()

    ## Create a progress bar with tqdm
    #progress_bar = tqdm(total=len(image_list), desc='Processing Images')

    for image in image_list:
        # Remove numbers and dashes from the filename for comparison
        if platform == "invokeai":
            simplified_image = image
        else:
            simplified_image = ''.join(filter(str.isalpha, os.path.splitext(image)[0]))

        # Skip already matched images
        if image in matched_pairs:
            progress_bar.update(1)
            continue

        pair_found = False
        image_pairs = None

        # Search for images with the same simplified filename
        for compare_image in image_list:
            if image != compare_image:
                if platform == "invokeai":
                    compare_simplified_image = image
                else:
                    compare_simplified_image = ''.join(filter(str.isalpha, os.path.splitext(compare_image)[0]))

                # Check if the simplified filenames match
                if platform == "invokeai":
                    image_path_1 = os.path.join(folder_path, image)
                    image_path_2 = os.path.join(folder_path, compare_image)

                    # Extract metadata for the image pair
                    value_1, extra_info_1 = extract_metadata(image_path_1, platform)
                    value_2, extra_info_2 = extract_metadata(image_path_2, platform)

                    # Compare the metadata values
                    if value_1 == value_2:
                        image_pairs = (image_path_1, image_path_2)
                        matched_pairs.add(image)
                        matched_pairs.add(compare_image)
                        pair_found = True
                        break
                else:
                    if simplified_image == compare_simplified_image:
                        image_path_1 = os.path.join(folder_path, image)
                        image_path_2 = os.path.join(folder_path, compare_image)
    
                        # Extract metadata for the image pair
                        value_1, extra_info_1 = extract_metadata(image_path_1, platform)
                        value_2, extra_info_2 = extract_metadata(image_path_2, platform)
    
                        # Compare the metadata values
                        if value_1 == value_2:
                            image_pairs = (image_path_1, image_path_2)
                            matched_pairs.add(image)
                            matched_pairs.add(compare_image)
                            pair_found = True
                            break

        if pair_found:
            # Remove matched images from the image list
            image_list = [img for img in image_list if img not in matched_pairs]



        if image_pairs:
            # Yield the image pair
            yield image_pairs



def image_comparison_start_pickapic(input_folder, platform):
    # Create the image pair generator
    generator = image_pair_generator(input_folder, platform)
    # Get the next unique image pair
    images = next(generator)

    imagepath1 = images[0]
    imagepath2 = images[1]
    image1 = Image.open(images[0])
    image2 = Image.open(images[1])
    prompt1, extra_info1 = extract_metadata(images[0], platform)
    prompt2, extra_info2 = extract_metadata(images[1], platform)
    return image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2

def image_comparison_select1_pickapic(input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform):
    bothbad = "False"
    add_data_to_csv(imagepath2, imagepath1, prompt1, extra_info1, bothbad, platform)
    # Create the image pair generator
    generator = image_pair_generator(input_folder, platform)
    # Get the next unique image pair
    images = next(generator)
    imagepath1 = images[0]
    imagepath2 = images[1]
    image1 = Image.open(images[0])
    image2 = Image.open(images[1])
    prompt1, extra_info1 = extract_metadata(images[0], platform)
    prompt2, extra_info2 = extract_metadata(images[1], platform)
    return image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2 

def image_comparison_select2_pickapic(input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform):
    bothbad = "False"
    add_data_to_csv(imagepath2, imagepath1, prompt1, extra_info1, bothbad, platform)
    # Create the image pair generator
    generator = image_pair_generator(input_folder, platform)
    # Get the next unique image pair
    images = next(generator)
    imagepath1 = images[0]
    imagepath2 = images[1]
    image1 = Image.open(images[0])
    image2 = Image.open(images[1])
    prompt1, extra_info1 = extract_metadata(images[0], platform)
    prompt2, extra_info2 = extract_metadata(images[1], platform)
    return image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2 
def image_comparison_skip_pickapic(input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform):
    bothbad = "True"
    add_data_to_csv(imagepath2, imagepath1, prompt1, extra_info1, bothbad, platform)
    # Create the image pair generator
    generator = image_pair_generator(input_folder, platform)
    # Get the next unique image pair
    images = next(generator)
    imagepath1 = images[0]
    imagepath2 = images[1]
    image1 = Image.open(images[0])
    image2 = Image.open(images[1])
    prompt1, extra_info1 = extract_metadata(images[0], platform)
    prompt2, extra_info2 = extract_metadata(images[1], platform)
    return image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2

def selectplatform(choice):
    platform.click(fn=image_comparison_start_pickapic, inputs=[input_folder, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])

theme = gr.themes.Base().set(
    button_large_padding='*spacing_xxl',
    button_large_radius='*radius_xxl',
    button_large_text_size='*text_xxl',
)
with gr.Blocks(theme=theme) as demo:
    filepath = "W:/webui backup/automatic/outputs/text"
    with gr.Column(scale=2):#(scale=2):
        with gr.Tab("pickapic"):
            with gr.Row():
                input_folder = gr.Textbox(label="input folder")
            with gr.Row():
                platform = gr.Radio(label='images in the folder made with:', choices=["automatic1111", "vlad-automatic", "invokeai", "DeepFloyd-IF-webUI","kandinsky2.1-kubin"])
            #with gr.Row():
                #startpickapic = gr.Button("start")
            with gr.Row():
                prompt1 = gr.outputs.Textbox(label="prompt")
            with gr.Row(visible=False):
                prompt2 = gr.outputs.Textbox(label="prompt")
            with gr.Row():
                image1 = gr.Image(type="pil", label="Image").style(height=512)
                image2 = gr.Image(type="pil", label="Image").style(height=512)
            with gr.Row(visible=False):
                imagepath1 = gr.outputs.Textbox(label="imagepath")
                imagepath2 = gr.outputs.Textbox(label="imagepath")
            with gr.Row(visible=False):
                extra_info1 = gr.outputs.Textbox(label="imagepath")
                extra_info2 = gr.outputs.Textbox(label="imagepath")
            with gr.Row():
                select_image1 = gr.Button("Image 1")
                select_image2 = gr.Button("Image 2")
            with gr.Row():
                select_skip = gr.Button("Neither")
            
        #pickapic type rating
        platform.change(fn=image_comparison_start_pickapic, inputs=[input_folder, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])
        #startpickapic.click(fn=image_comparison_start_pickapic, inputs=[input_folder, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])
        select_image1.click(fn=image_comparison_select1_pickapic, inputs=[input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])
        select_image2.click(fn=image_comparison_select2_pickapic, inputs=[input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])
        select_skip.click(fn=image_comparison_skip_pickapic, inputs=[input_folder, prompt1, extra_info1, imagepath1, imagepath2, platform], outputs=[image1, prompt1, imagepath1, image2, prompt2, imagepath2, extra_info1, extra_info2])


demo.launch()