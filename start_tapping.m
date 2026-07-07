% this is the only script that needs to be started

%% at the beginning the participant number has to be given
% parameters
prompt = {'Subject number:'};
dlg_title = 'Set parameters';
num_lines = 1;
tmp= inputdlg(prompt,dlg_title,num_lines);
subject                     = tmp{1};
parameter.subject_code      = tmp{1};
 
parameter.debugging          =1;  % 1: debugging mode; should be 0 when participant is run1

rng('shuffle');

%% run the experiment
% 

main_experiment_start(parameter);

RestrictKeysForKbCheck([]);
ShowCursor;
Screen('CloseAll');
