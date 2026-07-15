function demo_start(parameter)
rng('shuffle');



%% folder information

parameter.save_path                   = [pwd filesep 'save' filesep parameter.subject_code];

% generate the participant folder if it doesn't exist;
if ~(exist(parameter.save_path) == 7)
    mkdir(parameter.save_path)
end
parameter.filename                    = [parameter.subject_code];

%% session information
% is saved automatically
parameter.date             = 0;
parameter.start_time       = 0;
parameter.end_time         = 0;


%% auditory display
parameter.audio_input_channel                         = 0;
if parameter.debugging == 1
    parameter.audio_output_channel                    = 1; 
else
    parameter.audio_output_channel                    = 1;
end
parameter.audio_output_freq                           = 44100;
parameter.amplitude_mod                               = 10;

%% response; watch out response keys defined in present stimuli
if parameter.debugging == 1
    [parameter.response_device_number, productNames, allInfos] = GetKeyboardIndices;

else
    [parameter.response_device_number, productNames, allInfos] = GetKeyboardIndices;
    
end
parameter.manual_pause_key                            = 'p';

%% Do the synchtest (all other parts of the experiment are performed at the BIC MEG lab

cd 'main_exp/'
demo(parameter)
Screen('CloseAll');
cd ..


