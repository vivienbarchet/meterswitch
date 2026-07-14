function signal = create_sine(fs, bpm, totalDur, toneDur, fLow, fHigh, meter)

beatDur = 60 / bpm;

nSamplesTotal = round(totalDur * fs);
signal = zeros(1, nSamplesTotal);

toneSamples = round(toneDur * fs);

% precompute one tone (reuse for speed/consistency)
tTone = (0:toneSamples-1) / fs;

% number of tone onsets
nBeats = floor(totalDur / beatDur);

% convert beat spacing to samples ONCE (critical for precision)
beatSamples = round(beatDur * fs);

if isnumeric(meter)
    emphasized = 1:meter:200;
else
    emphasized = [];
end

for i = 1:nBeats
    
    onset = (i-1) * beatSamples + 1;
    offset = onset + toneSamples - 1;
    
    if offset > nSamplesTotal
        break;
    end
    
    if ismember(i, emphasized)
        freq = fHigh;
    else
        freq = fLow;
    end
    
    tone = sin(2*pi*freq*tTone);
    %add hann window
    N = length(tone);
    win = hann(N)';     % Create Hann window and transpose to a row vector
    tone = tone .* win; % Multiply point-by-point
        
    % hard placement (no drift accumulation possible)
    signal(onset:offset) = signal(onset:offset) + tone;
end

% normalize to avoid clipping (important for PTB safety)
signal = signal / max(abs(signal));
end