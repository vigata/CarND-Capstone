import yaml
import os.path
import pickle
import sys
import numpy as np
import cv2

files_dir = '../Bosch/'
samples_file = 'train.yaml'
samples_pickle_path = './train.pickle'

samples_file_path = os.path.join(files_dir, samples_file)

green_labels = ('GreenStraightRight', 'GreenStraightLeft', 'GreenStraight', 'GreenRight', 'Green', 'GreenLeft')
yellow_labels = ('Yellow')
red_labels = ('RedStraightLeft', 'RedStraight', 'RedRight', 'RedLeft', 'Red')

# Taken from TrafficLight message definition
# ros/src/styx_msgs/msg/TrafficLight.msg
UNKNOWN = 4
GREEN = 3
YELLOW = 1
RED = 0

IMG_WIDTH = 1280
IMG_SIDE_CROP = 180
IMG_SIDE_LIGHT_TOLERANCE = 10

def samples_from_storage():
    samples = None
    if (os.path.isfile(samples_pickle_path)):
        print('Loading samples from {} ...'.format(samples_pickle_path))
        with open(samples_pickle_path, 'r') as samples_pickle_file:
            samples = pickle.load(samples_pickle_file)
    else:
        with open(samples_file_path, 'r') as stream:
            try:
                print('Loading samples from {} ...'.format(samples_file_path))
                samples = yaml.load(stream)
                print('Loaded samples from {}'.format(samples_file_path))
                try:
                    with open(samples_pickle_path, 'w') as samples_pickle_file:
                        pickle.dump(samples, samples_pickle_file)
                except IOError, err:
                    print('Could not write {}: {}'.format(samples_pickle_path, err))
            except yaml.YAMLError as exc:
                print(exc)
    return samples

def null_transform(samples):
    return samples

def is_light_in_bounds(light):
    if 'x_max' in light and light['x_max'] < 0 + (IMG_SIDE_CROP + IMG_SIDE_LIGHT_TOLERANCE):
        return False
    if 'x_min' in light and light['x_min'] > IMG_WIDTH - (IMG_SIDE_CROP + IMG_SIDE_LIGHT_TOLERANCE):
        return False
    return True

def filtered_out_of_bounds_lights(boxes):
    return filter(is_light_in_bounds, boxes)

def log_remaining_samples(transform):
    def wrapper(samples):
        print('Applying transform {} to samples'.format(transform.__name__))
        samples_after_transform = transform(samples)
        print('{} samples remain'.format(len(samples_after_transform)))
        return samples_after_transform
    return wrapper

def transformed_samples(samples, transforms):
    return reduce(lambda samples, transform: transform(samples), transforms, samples)

@log_remaining_samples
def cropped_labels_removed_transform(samples):
    for sample in samples:
        sample['boxes'] = filtered_out_of_bounds_lights(sample['boxes'])
    return samples

def is_light_on(light):
    return light['label'] != 'off'

def off_lights_removed(boxes):
    return filter(is_light_on, boxes)

@log_remaining_samples
def off_lights_removed_transform(samples):
    for sample in samples:
        sample['boxes'] = off_lights_removed(sample['boxes'])
    return samples

def sample_has_single_color_lights(sample):
    red_flag = False
    yellow_flag = False
    green_flag = False
    for light in sample['boxes']:
        label = light['label']
        if label in red_labels:
            red_flag = True
        if label in yellow_labels:
            yellow_flag = True
        if label in green_labels:
            green_flag = True
    flags = [red_flag, yellow_flag, green_flag]
    flags_as_ints = map(lambda x: int(x), flags)
    return sum(flags_as_ints) < 2

@log_remaining_samples
def multi_light_images_removed_transform(samples):
    return filter(sample_has_single_color_lights, samples)

# "Pure" as in lights are a single color
def label_for_pure_sample(sample):
    boxes = sample['boxes']
    if len(boxes) == 0:
        return UNKNOWN
    # Given filtering of offs and multiple colors, the
    # first entry should be representative of whole set
    light_label = boxes[0]['label']
    if light_label in red_labels:
        return RED
    if light_label in yellow_labels:
        return YELLOW
    if light_label in green_labels:
        return GREEN
    return UNKNOWN

@log_remaining_samples
def labeled_samples_transform(samples):
    for sample in samples:
        sample['label'] = label_for_pure_sample(sample)
    return samples

def samples_of_color(samples, color):
    return filter(lambda sample: sample['label'] == color, samples)

def main():
    samples = samples_from_storage()
    if samples is None:
        print('No samples to work with')
        sys.exit()

    print('Total samples: {}'.format(len(samples)))

    transforms = [
        cropped_labels_removed_transform,
        off_lights_removed_transform,
        multi_light_images_removed_transform,
        labeled_samples_transform
    ]
    final_samples = transformed_samples(samples, transforms)

    print("{} red samples".format(len(samples_of_color(final_samples, RED))))
    print("{} yellow samples".format(len(samples_of_color(final_samples, YELLOW))))
    print("{} green samples".format(len(samples_of_color(final_samples, GREEN))))
    print("{} unknown samples".format(len(samples_of_color(final_samples, UNKNOWN))))

if __name__ == '__main__':
    main()
