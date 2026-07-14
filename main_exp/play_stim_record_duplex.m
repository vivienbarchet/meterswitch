function [playbackstart, stopTime, resp_com, respt] = play_stim_record(subject,parameter, listen_sound, Fs, cond, phase, trialnum)
%% visual display
screen_color        = parameter.screen_color;
instruction_size    = parameter.instruction_size;
instruction_color   = parameter.instruction_color;
cross_color         = parameter.cross_color;
cross_size          = parameter.cross_size;
rect                = parameter;
my_window           = parameter.my_window;
trigger_duration = 0.005;

listen_sound   = [listen_sound'; listen_sound'];
tiempo_L                = size(listen_sound,1)/Fs; %tiempo_L=2;

KbReleaseWait;




%% set fixation cross
fixation_cross = '+';
Screen('TextSize', my_window, cross_size);
DrawFormattedText(my_window, fixation_cross, 'center', 'center', [cross_color cross_color cross_color]);
Screen(my_window, 'Flip');
WaitSecs(0.5 + 0.25*rand)

% Parform low-level initialization of the sound driver:
InitializePsychSound(1);
% Provide some debug output:
PsychPortAudio('Verbosity', 10);

tiempo_L=size(listen_sound,2)/Fs;
pa = PsychPortAudio('Open', [], 3, 3, Fs, [2 3]); % devid, mode (3=fullduplex), reqlatency (3=full control, agressive), freq, channels [output, input]
PsychPortAudio('GetAudioData', pa, tiempo_L);
PsychPortAudio('FillBuffer', pa, listen_sound);
painputstart = PsychPortAudio('Start', pa, 1, 0, 1);

% Start audio capture

WaitSecs(tiempo_L-0.01);

[audiodata, offset, overrun] = PsychPortAudio('GetAudioData', pa);
PsychPortAudio('Stop', pa, 1);
PsychPortAudio('Close');
fileOut =([parameter.save_path  '/' cond '_famil' '.wav']);
audiowrite(fileOut, audiodata', Fs);


end

