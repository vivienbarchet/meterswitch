function main_experiment(parameter)

% Subject parameters
subject= parameter.subject_code;

%% Screen Configurations
parameter.cross_size                                    = 200;
parameter.cross_color                                   = 220;
parameter.screen_refresh_rate                           = 60;
parameter.instruction_size                              = 40;
parameter.instruction_color                             = 220;
parameter.screen_color                                  = 30;


parameter.save_pathf                   = [parameter.save_path filesep 'famil'];

if ~(exist(parameter.save_pathf) == 7)
    mkdir(parameter.save_pathf)
end

parameter.save_pathp                   = [parameter.save_path filesep 'prime'];

if ~(exist(parameter.save_pathp) == 7)
    mkdir(parameter.save_pathp)
end

parameter.save_patht                 = [parameter.save_path filesep 'test'];

if ~(exist(parameter.save_patht) == 7)
    mkdir(parameter.save_patht)
end


%% set up visual settings
rng('shuffle');

%% hardware preparation
%% visual display
screen_color    = parameter.screen_color;
Screen('Preference', 'SkipSyncTests', 1)
% visual parameter
instruction_size    = parameter.instruction_size;
instruction_color   = parameter.instruction_color;
cross_size          = parameter.cross_size;
cross_color         = parameter.cross_color;

% Open a window
AssertOpenGL;
screens         = Screen('Screens');
screenNum       = 0;

if parameter.debugging ==1
    % debug window
    [my_window, rect] = Screen('OpenWindow', screenNum, [screen_color screen_color screen_color], [0,0,500,500]);
else
    % experiment window
    [my_window, rect] = Screen('OpenWindow', screenNum, [screen_color screen_color screen_color]);
    HideCursor;
end
parameter.rect      = rect;
parameter.my_window = my_window;

% Set Debuglevel to 3
Screen('Preference', 'visualDebuglevel', 3);

% skip the screen synchronization test
AssertOpenGL;
Screen('Preference', 'SkipSyncTests', 1);

% Set Priority level
priorityLevel = MaxPriority(my_window);
Priority(priorityLevel);

% make sure that none of restricted keys are being pushed
if ismac == 1
    while KbCheck end
else
    while KbCheck end
end

disp('keyboard restricted.');

%%


first_welcome = ['In this experiment, you will hear tones and tap to the rhythm of these tones.\n\n ' ...
    'Please tap on the marked area of the table in front of you.\n\n ' ...
    'Please tap to the rhythm of the tones, emphasizing the same grouping.\n\n ' ...
    'Press any key to continue.'];
    
print_instruction_new(my_window, rect,first_welcome, instruction_size, instruction_color);



InitializePsychSound(1);
PsychPortAudio('Verbosity', 10);




%%% Familarization with the two meters
fs = 48000;
bpm = 110;
totalDur = 60;
toneDur = 0.05;
fLow = 440;
fHigh = 600;

meter = 2:3;
metershuff = meter(randperm(numel(meter)));

for tt = 1:2
    meter = metershuff(tt);
    f1 = create_sine(fs, bpm, totalDur, toneDur, fLow, fHigh, meter);

    %%%Trial loop 
    play_stim_record(subject, parameter, f1, fs, meter, 'famil', tt);

    i1 = ['Well done! \n\n' ...
        'Now, you will hear another rhythm. Please tap along with this rhythm.\n\n' ...
        'Press any key to continue.'];
    if tt == 1  
        print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);
    end


end

i1 = ['Great!\n\n' ...
      'Now, you will hear briefly hear one of these rhythms.\n\n' ...
      'Please tap along with this rhythm.\n\n' ...
      'Afterwards, you will hear a sequence of unaccented tones.\n\n' ...
      'First, you will continue to tap using the grouping you heard before.\n\n'...
      'Then, you will either receive a cue to switch to the other grouping \n\n' ...
      'or you will spontaneously switch from one to the other.\n\n\n'...
      'The frequency of the tones will not change within the sequence.\n\n\n' ...
      'Press any key to continue.'];
    
print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);

%%Actual trial loop 
numtrials = 20;
meterlist = [2 3];
condlist = ["cued","spontaneous"];

numTrialsPerCombination = 5;

%% Create balanced design
meter = [];
condition = [];

for c = 1:numel(condlist)
    for m = 1:numel(meterlist)
        meter = [meter; repmat(meterlist(m), numTrialsPerCombination, 1)];
        condition = [condition; repmat(condlist(c), numTrialsPerCombination, 1)];
    end
end

trials = table(condition, meter);

%% Shuffle trial order
trials = trials(randperm(height(trials)), :);

%% Random BPM assignment
bpmlist = 100:4:120;
trials.BPM = bpmlist(randi(numel(bpmlist), height(trials), 1))';

%% Switch times
switchtimes = 12:2:18;  

trials.SwitchTime = zeros(height(trials),1);

isCued = trials.condition == "cued";
nCued = sum(isCued);

trials.SwitchTime(isCued) = switchtimes(randi(numel(switchtimes), nCued, 1));


trialdur = 30;
primedur = 10;



results = trials;


for tt = 1:numtrials
    meter = trials(tt, "meter").meter;
    bpm = trials(tt, "BPM").BPM;

    condi = trials(tt, "condition").condition;
    
    %create prime
    f1 = create_sine(fs, bpm, primedur, toneDur, fLow, fHigh, meter);
    %create unaccented sequence
    f2 = create_sine(fs, bpm, trialdur, toneDur, fLow, fHigh, 'none');

    i1 = ['This is trial ' num2str(tt) ' of 20.\n\n' ...
        'Listen to the following sound and tap along.\n\n' ...
        'Press any key to continue.'];
    
    print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);
    
    %prime
    play_stim_record(subject, parameter, f1, fs, meter, 'prime', tt);

    i1 = ['Now, you will listen to an unaccented sequence of sounds.\n\n' ...
        'Please continue to tap in the grouping that you just heard.\n\n'...
        'Press any key to continue.'];
    
    print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);

    if condi == "cued"
        i1 = ['This is a cued trial.\n\n'...
            'Please switch to the alternative grouping when the cross changes its color.\n\n' ...
            'Press any key to start.'];
    else
        i1 = ['This is a spontaneous trial.\n\n'...
            'Please switch to the alternative grouping whenever you want (but only once per trial).\n\n' ...
            'Press any key to start.'];
    end
    print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);


    %switchtrial
    if condi == "cued"
        switchtime = trials(tt, "SwitchTime").SwitchTime;
        play_stim_record_cued(subject, parameter, f2, fs,condi, meter, switchtime, tt);
    
    else
        play_stim_record_spontaneous(subject, parameter, f2, fs, meter, 'test', tt, condi);
        
    end
    
    


    results.Subject(tt)     = string(subject);
    results.TrialNumber(tt) = tt;


    switchq = ['Did you switch the meter during the trial?\n\n' ...
        'Press 1 for yes and 2 for no.'];

    Screen('TextSize', my_window, instruction_size);
    DrawFormattedText(my_window,switchq, 'center', 'center', [instruction_color instruction_color instruction_color]);
    Screen(my_window, 'Flip');

    yes = KbName('1!');
    no = KbName('2@');

    RestrictKeysForKbCheck([50,49]);
    key = 0;
    while ~key
        [key, keyTime, keyCode] = KbCheck;
        WaitSecs(0.05);
    end
    
    resp_com = keyCode(yes);

    results.switch(tt)     = resp_com;

    RestrictKeysForKbCheck([]);
end

% Save CSV
outfile = fullfile(parameter.save_path, sprintf('%s_log.csv', subject));
writetable(results, outfile);


i1 = ['You have finished the experiment.\n\n' ...
    'Thank you!'];
print_instruction_new(my_window, rect,i1, instruction_size, instruction_color);

end








