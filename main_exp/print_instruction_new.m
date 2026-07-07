function print_instruction_new(my_window, rec, instruction, stimuli_size, stimuli_color)
stimuli_color = [stimuli_color stimuli_color stimuli_color];
Screen(my_window,'TextFont','Helvetica');
Screen('TextSize',my_window, stimuli_size);
DrawFormattedText(my_window, instruction, 'center', 'center', stimuli_color);

%DrawFormattedText(my_window, '... Weiter gehts per Tastendruck ...', 'center', rec(4)-rec(4)/7.5, stimuli_color);                            
Screen(my_window, 'Flip');
%KbWait();

KbQueueCreate
KbQueueStart
ok = 0;
while ~ok
    [pressed, ~] = KbQueueCheck;
    if pressed
        ok = 1;
    end
end


end
