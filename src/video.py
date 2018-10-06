import cv2
import sys
from mvnc import mvncapi

from src.utils import resize_image, draw_boxes
from src.box_utils import scale_box
from src.pipeline import Pipeline
from src.mvnc_detector import Detector
from src.iou_tracker import IOUTracker

def process(video_in, video_out, pipeline, headless=True):
    """Run video through pipeline"""
    while video_in.isOpened():
        ok, frame = video_in.read()
        if not ok:
            print('Error reading video')
            break

        # quit
        if not headless:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # main loop
        tracks = pipeline.forward(frame)
        print("tracks: %s" % tracks)
        boxes = [track['box'] for track in tracks]
        boxes = [scale_box(box, frame) for box in boxes]
        print("boxes: %s" % boxes)
        frame = draw_boxes(frame, boxes)

        # display resulting frame
        if not headless:
            cv2.imshow('Video', frame)

        # Write the frame into output file
        video_out.write(frame)


def init_device():
    # Get a list of ALL the sticks that are plugged in
    # we need at least one
    device_list = mvncapi.enumerate_devices()
    if len(device_list) == 0:
        print('No devices found')
        quit()

    # Pick the first stick to run the network
    device = mvncapi.Device(device_list[0])

    # Open the NCS
    device.open()
    return device 

def setup_detector(device, detector_name=None):
    """Setup detector"""
    detector = Detector('./models/voc2012/config.yml', device)
    return detector

def setup_tracker():
    return IOUTracker()

def run_video(input_filepath, output_filepath, detector_name, event_interval=6):
    """
    Args:
        input_filepath: input video filepath. Set to 0 for webcam, or other device no.
        output_filepath: filepath to save result video
        detector_name: detector to be used
        event_interval: delay between each detector call, default=6 seconds.
    """
    if input_filepath == "0":
        input_filepath = 0
    video_capture = cv2.VideoCapture(input_filepath)

    # exit if video not opened
    if not video_capture.isOpened():
        print('Cannot open video')
        sys.exit()
    
    # Default resolutions of the frame are obtained.The default resolutions are system dependent.
    # We convert the resolutions from float to integer.
    frame_width = int(video_capture.get(3))
    frame_height = int(video_capture.get(4))
    
    # Define the codec and create VideoWriter object.The output is stored in 'outpy.avi' file.
    video_out = cv2.VideoWriter(output_filepath, 
        cv2.VideoWriter_fourcc(*'MPEG'), 
        20., 
        (frame_width,frame_height))

    # init detector
    device = init_device()
    detector = setup_detector(device, detector_name)

    # init tracker
    tracker = setup_tracker()

    # init detection pipeline
    # TODO: pass image_size config  
    pipeline = Pipeline(detector=detector, tracker=tracker, resize_image_size=(300,300))

    # run processing
    process(video_capture, video_out, pipeline, headless=False)

    # When everything is done, release the capture
    video_capture.release()
    cv2.destroyAllWindows()

    # shutdown device
    detector.close()
    device.close()
    device.destroy()



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_filepath", "-i", type=str,
        action='store',
        help='Input filepath')
    parser.add_argument("--output_filepath", "-o", type=str,
        action='store',
        help='Output filepath')
    parser.add_argument("--detector", "-d", type=str,
        action='store',
        help='Detector model, [voc|mscoco|safety]')
    parser.add_argument("--interval", "-n", type=int,
        action='store',
        default=6,
        help='Detection interval in seconds, default=6')

    args = parser.parse_args()
    run_video(args.input_filepath, args.output_filepath, args.detector, 
        args.interval)
