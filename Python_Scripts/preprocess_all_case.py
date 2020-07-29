import os
import matplotlib.pyplot as plt
import pandas as pd
from pydub import AudioSegment
from os import listdir
from os.path import isfile, join
import argparse
from ketos.data_handling import selection_table as sl
import librosa
from skimage.restoration import (denoise_wavelet)
import soundfile as sf
from scipy import signal


# Function to add the end time
def add_end(filename):
    """
    Adds the parameter called end which is the
    end_time to the .tsv/csv file.

    Returns:same tsv/csv file with an extra parameter of end_time.
    """
    filename["end"] = filename["start"] + filename["duration_s"]


# Generate mean and annot-train
def duration_mean(filename):
    """
    Reads the .tsv/csv file and calculates the mean.

    Returns:mean and the pandas tsv/csv file.
    """
    annot_train = pd.read_csv(filename, sep='\t')
    mean = annot_train['duration_s'].mean()
    return annot_train, mean


# Function to find extract filename and start time
def fname_stime(filename):
    """
    Reads the file name and the start time from the given file from
    which the calls are to be extracted.

    Returns:file_name and the start_time.
    """
    file_name = filename.iloc[:, 0].values
    start_time = filename.iloc[:, 1].values
    return file_name, start_time


def extract_audio(
    label,
    filename,
    output_directory,
    position,
    file_location,
    call_time_in_seconds
                ):
    """
    This function extracts the audio from the .wav files to generate
    smaller audio clips of particular time frame which is used to
    get the complete positive and negative calls.

    Here the enter the call duration in variable call_time_in_seconds
    Since the audio segment assumes 3000 as 3 second, therefore, we
    would multiply the time entered by user by 1000.

    Enter the output directory name in the output_directory
    Returns:the extracted calls of shorter time frames containing only
    the calls or no calls.
    """
    base_path = os.getcwd()
    # make directory if it does not exist
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)
    outpath = os.path.join(base_path, output_directory)
    file_name = filename.iloc[:, 0].values
    start_time = filename.iloc[:, position].values
    i = 0
    o = 0
    call_time_in_seconds = call_time_in_seconds*1000
    os.chdir(file_location)
    # Enter the file location of the calls directory
    for x in file_name:
        AUDIO_FILE = x
        sound = AudioSegment.from_file(AUDIO_FILE)
        p = start_time[i]
        p = p * 1000
        print(p)
        i = i + 1
        o = p + call_time_in_seconds
        call = sound[p:o]
        call.export(outpath + label + "calls{0}.wav".format(i),
                    format="wav")


# Applying PCEN(Per_Channel_Energy_Normalization)
def apply_per_channel_energy_norm(data, sampling_rate):
    """
    PCEN is a computationally efficient frontend for robust detection
    and classification of acoustic events in heterogeneous environments.
    In this step we are going to apply PCEN.
    """
    S = librosa.feature.melspectrogram(
        data, sr=sampling_rate, power=1)  # Compute mel-scaled spectrogram
    # Convert an amplitude spectrogram to dB-scaled spectrogram
    pcen_S = librosa.core.pcen(S)
    return pcen_S


# Applying Wavelet-Denoising
def wavelet_denoising(data):
    '''
    Wavelet Denoising using scikit-image
    NOTE: Wavelet denoising is an effective method
    for SNR improvement in environments with
              wide range of noise types competing
               for the same subspace.
    '''
    im_bayes = denoise_wavelet(
                  data, multichannel=False,
                  convert2ycbcr=False,
                  method='BayesShrink',
                  mode='soft')

    '''
    VisuShrink is designed to eliminate noise with high probability,
    but this results in a visually over-smooth appearance.
    Here, we specify a reduction in the threshold by
    factors of 2 and 4.
    '''

    return im_bayes


# Plotting the spectrogram
def plot_spectrogram(base, plot, calls):
    """
    Plots the spectrograms from the audio files of the extracted calls.
    """
    basePath = base
    plotPath = join(basePath, plot)
    folderpath = join(basePath, calls)
    onlyfiles = [f for f in listdir(folderpath)
                 if isfile(join(join(folderpath, f)))]
    for idx, file in enumerate(onlyfiles):
        data, samplerate = sf.read(join(folderpath, file))
        f, t, spec = signal.spectrogram(data, samplerate)
        filename = file.split(sep=".")[0]

        fig, ax = plt.subplots(1, 1)
        ax.specgram(data, Fs=samplerate, NFFT=1024)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        os.chdir(plotPath)

        plt.savefig(join(plotPath, filename + ".png"))
        plt.close(fig)


# Plot the graph and save them
def plot_and_save(denoised_data, f_name, plotPath):

    fig, ax = plt.subplots()

    i = 0

    ax.imshow(denoised_data)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    fig.set_size_inches(10, 10)
    os.chdir(plotPath)
    fig.savefig(
        f"{f_name[:-4]}" + "_{:04d}.png".format(i),
        dpi=80,
        bbox_inches="tight",
        quality=95,
        pad_inches=0.0)

    fig.canvas.draw()
    fig.canvas.flush_events()
    i += 1
    plt.close(fig)


# Plot the graph generated from denoised data
def final_plot(base_path, plot_path, folder_path, preprocess_case):

    basePath = base_path
    plotPath = join(basePath, plot_path)
    folderpath = join(basePath, folder_path)
    onlyfiles = [f for f in listdir(folderpath) if isfile(
        join(join(folderpath, f)))]

    for idx, file in enumerate(onlyfiles):
        data, sr = librosa.core.load(
                    os.path.join(folderpath, file), res_type='kaiser_best')
        f_name = os.path.basename(file)
        pcen_S = apply_per_channel_energy_norm(data, sr)
        if preprocess_case == 3:
            denoised_data = wavelet_denoising(pcen_S)
        else:
            denoised_data = pcen_S
        plot_and_save(denoised_data, f_name, plotPath)


# Enter the base_path, the current path, and the name of the tsv file that
# you want to read

def main(args):
    # Enter the base_path, the current path, and the name of the tsv
    # file that
    # you want to read
    tsv_path = args.tsvpath
    audios_path = args.audiospath
    call_time = args.calltime
    output_path_positive = args.outputpathpositive
    output_path_negative = args.outputpathnegative
    output_plot_path_pos = args.outputplotpathpos
    output_plot_path_neg = args.outputplotpathneg
    base_path = os.getcwd()
    preprocess_case = args.preprocesscase
    # Enter the path of the standardized tsv's
    annot_train, mean = duration_mean(tsv_path)
    print("The mean of the call duration is {}".format(mean))
    add_end(annot_train)

    # make directory if it does not exist
    if not os.path.isdir(output_path_positive):
        os.mkdir(output_path_positive)
    if not os.path.isdir(output_path_negative):
        os.mkdir(output_path_negative)
    if not os.path.isdir(output_plot_path_pos):
        os.mkdir(output_plot_path_pos)
    if not os.path.isdir(output_plot_path_neg):
        os.mkdir(output_plot_path_neg)
    # Extract the audio of the calls
    extract_audio(
        "round2_calls", annot_train,
        output_path_positive, 1,
        audios_path, call_time)

    map_to_ketos_annot_std = {'wav_filename': 'filename'}
    std_annot_train2 = sl.standardize(
                           table=annot_train,
                           signal_labels=["SRKWs"],
                           mapper=map_to_ketos_annot_std,
                           trim_table=True)

    '''
    Since we also want the negative audio, we would generate
    negative sound by extracting it from the background sound
    what are not present in  the call duration. For that first
    we create a tsv that generates time-interval from the tsv
    files that are not within the start-time and end-time
    '''

    positives_train2 = sl.select(
                            annotations=std_annot_train2,
                            length=call_time)
    file_durations_train2 = sl.file_duration_table(
                                audios_path)
    negatives_train2 = sl.create_rndm_backgr_selections(
                            annotations=std_annot_train2,
                            files=file_durations_train2,
                            length=call_time,
                            num=len(positives_train2),
                            trim_table=True)

    negatives_train2.to_csv(
                       base_path+'negative2.tsv',
                       mode='a',
                       sep='\t',
                       header=False)

    negatives_train2save = pd.read_csv(base_path+'negative2.tsv', sep='\t')

    extract_audio(
        'round2_calls_neg', negatives_train2save,
        output_path_negative, 2,
        audios_path, call_time)

    if preprocess_case == 3 or preprocess_case == 2:
        final_plot(
                  base_path,
                  output_plot_path_pos,
                  output_path_positive, preprocess_case)

        final_plot(
                  base_path,
                  output_plot_path_neg,
                  output_path_negative, preprocess_case)

    elif preprocess_case == 1:
        plot_spectrogram(
            base_path,
            output_plot_path_pos,
            output_path_positive)
        plot_spectrogram(
            base_path,
            output_plot_path_neg,
            output_path_negative)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Pre-Process the audio files")
    parser.add_argument(
        '-tsv',
        '--tsvpath',
        type=str,
        help='Enter the path to the tsv file',
        required=True)
    parser.add_argument(
        '-audiop',
        '--audiospath',
        type=str,
        help='Enter the path to the audio files',
        required=True)

    parser.add_argument(
        '-ctime',
        '--calltime',
        type=int,
        help='Enter the call time for which most of the calls are covered',
        required=True)

    parser.add_argument(
        '-opc',
        '--outputpathpositive',
        type=str,
        help='Enter the output path of the extracted positive calls',
        required=True)

    parser.add_argument(
        '-onc',
        '--outputpathnegative',
        type=str,
        help='Enter the output path where of the extracted negative ',
        required=True)

    parser.add_argument(
        '-case',
        '--preprocesscase',
        type=int,
        help='Enter the case with which we want to use to preprocess',
        required=True)

    parser.add_argument(
        '-opp',
        '--outputplotpathpos',
        type=str,
        help='Enter the output path where the spectrograms are extracted',
        required=True)

    parser.add_argument(
        '-opn',
        '--outputplotpathneg',
        type=str,
        help='Enter the output path where the spectrograms are extracted',
        required=True)

    args = parser.parse_args()

    main(args)