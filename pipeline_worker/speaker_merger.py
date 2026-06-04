import os
import sys
import json

sys.path.append(os.path.dirname(__file__))

def merge_speakers(diarization_path, transcription_path, session_folder):
    """
    Fusionne la diarisation et la transcription.
    Pour chaque segment texte, trouve quel speaker parlait.
    Retourne le chemin du fichier transcript_speakers.json
    """
    output_folder = os.path.join(session_folder, 'merged')
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, 'transcript_speakers.json')

    # Charge les deux fichiers
    with open(diarization_path, 'r', encoding='utf-8') as f:
        diarization = json.load(f)

    with open(transcription_path, 'r', encoding='utf-8') as f:
        transcription = json.load(f)

    # Pour chaque segment texte, trouve le speaker dominant
    merged = []
    for segment in transcription:
        speaker = _find_speaker(segment['start'], segment['end'], diarization)
        merged.append({
            "speaker": speaker,
            "start": segment['start'],
            "end": segment['end'],
            "text": segment['text']
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    for seg in merged:
        print(f" [{seg['speaker']}] [{seg['start']:.1f}s → {seg['end']:.1f}s] {seg['text']}")
    print(f"Fusion : {len(merged)} segments → {output_path}")
    return output_path

def _find_speaker(start, end, diarization):
    """
    Trouve le speaker qui parle le plus longtemps
    sur l'intervalle [start, end].
    """
    scores = {}
    for d in diarization:
        # Calcule le chevauchement entre le segment texte et le segment diarisation
        overlap_start = max(start, d['start'])
        overlap_end = min(end, d['end'])
        overlap = max(0, overlap_end - overlap_start)

        if overlap > 0:
            speaker = d['speaker']
            scores[speaker] = scores.get(speaker, 0) + overlap

    if not scores:
        return "UNKNOWN"

    # Retourne le speaker avec le plus grand chevauchement
    return max(scores, key=scores.get)