from pathlib import Path
import whisper
import logging
from typing import Optional, Any, Dict

def transcribe_audio(
    audio_file: str,
    model_name: str = "base",
    language: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper.

    Args:
        audio_file: Path to the audio file.
        model_name: Whisper model to use.
        language: Language code (optional).
        verbose: If True, show detailed output.

    Returns:
        Transcription result as a dictionary.
    """
    audio_path = Path(audio_file)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    logging.info(f"Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)

    logging.info(f"Transcribing {audio_path.name}...")

    result = model.transcribe(
        str(audio_path),
        language=language,
        verbose=verbose,
        fp16=False
    )

    logging.info("✓ Transcription complete")
    return result

def save_transcription(
    transcription: Dict[str, Any],
    output_file: str,
    include_timestamps: bool = False
) -> None:
    """
    Save transcription to text file.

    Args:
        transcription: The transcription result.
        output_file: Path to the output text file.
        include_timestamps: Whether to include timestamps in the output.
    """
    output_path = Path(output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        if include_timestamps:
            f.write("TRANSCRIPTION WITH TIMESTAMPS\n")
            f.write("="*50 + "\n\n")

            for segment in transcription['segments']:
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()

                start_time = f"{int(start//60):02d}:{int(start%60):02d}"
                end_time = f"{int(end//60):02d}:{int(end%60):02d}"

                f.write(f"[{start_time} - {end_time}] {text}\n")
        else:
            f.write("TRANSCRIPTION\n")
            f.write("="*50 + "\n\n")
            f.write(transcription['text'].strip())

        f.write("\n\n" + "="*50 + "\n")
        f.write("METADATA\n")
        f.write(f"Language: {transcription.get('language', 'auto-detected')}\n")
        if 'segments' in transcription:
            f.write(f"Duration: {transcription['segments'][-1]['end']:.1f} seconds\n")

    logging.info(f"✓ Transcription saved to: {output_path}")
