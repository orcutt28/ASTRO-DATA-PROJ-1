"""
Script to summarize abstracts of all papers using a chatbot.
"""

from pathlib import Path
import os
import time
import json

# Load environment variables BEFORE importing llm_units
env_file = Path(__file__).parent / "env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                os.environ[key] = value
                # If ASTRO1221_API_KEY is set, also set it as OPENAI_API_KEY
                if key == "ASTRO1221_API_KEY":
                    os.environ["OPENAI_API_KEY"] = value

from main import load_all_papers, Paper
from llm_units import summarize_text


def get_error_message(error):
    """
    Extract a user-friendly error message from an exception.
    """
    error_str = str(error)
    
    # Check for specific error types
    if "401" in error_str or "invalid_api_key" in error_str.lower():
        return "Invalid API key. Please check your API key in the env file and ensure it's valid at https://platform.openai.com/account/api-keys"
    elif "429" in error_str or "insufficient_quota" in error_str.lower():
        return "Quota exceeded. Please check your OpenAI account billing and usage limits at https://platform.openai.com/account/billing"
    elif "rate_limit" in error_str.lower():
        return "Rate limit exceeded. The script will wait and retry, or you can increase the delay between requests."
    elif "timeout" in error_str.lower():
        return "Request timed out. Please check your internet connection and try again."
    else:
        # Try to extract a cleaner error message
        if "error" in error_str.lower() and "message" in error_str.lower():
            try:
                # Try to parse JSON error if present
                if "{" in error_str:
                    start = error_str.find("{")
                    end = error_str.rfind("}") + 1
                    error_json = json.loads(error_str[start:end])
                    if "error" in error_json and "message" in error_json["error"]:
                        return error_json["error"]["message"]
            except:
                pass
        return error_str


def summarize_all_abstracts(output_file="summaries.txt", delay_between_requests=1):
    """
    Load all papers, extract abstracts, and summarize each using the chatbot.
    
    Args:
        output_file: Path to output file where summaries will be saved
        delay_between_requests: Seconds to wait between API requests (to avoid rate limits)
    """
    # Load all papers
    print("Loading papers...")
    papers = load_all_papers()
    print(f"Found {len(papers)} papers\n")
    
    # Check if OpenAI API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set.")
        print("Please set it in your env file or as an environment variable.")
        return
    else:
        # Show first and last few characters for verification (without exposing full key)
        print(f"✓ Using API key: {api_key[:10]}...{api_key[-10:]}\n")
    
    summaries = []
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    # Process each paper
    for i, paper in enumerate(papers, 1):
        if not paper:
            continue
            
        print(f"[{i}/{len(papers)}] Processing Paper {i}: {paper.title[:60]}...")
        
        if not paper.abstract:
            print(f"  ⚠️  No abstract found for this paper. Skipping.\n")
            summaries.append({
                'paper_number': i,
                'title': paper.title,
                'abstract': '',
                'summary': 'No abstract available',
                'status': 'skipped'
            })
            skipped_count += 1
            continue
        
        print(f"  Abstract length: {len(paper.abstract)} characters")
        
        try:
            # Summarize the abstract
            print(f"  Generating summary...")
            summary = summarize_text(paper.abstract)
            
            summaries.append({
                'paper_number': i,
                'title': paper.title,
                'abstract': paper.abstract,
                'summary': summary,
                'status': 'success'
            })
            
            success_count += 1
            print(f"  ✓ Summary generated successfully ({len(summary)} characters)\n")
            
            # Delay to avoid rate limits
            if i < len(papers):
                time.sleep(delay_between_requests)
                
        except Exception as e:
            error_msg = get_error_message(e)
            print(f"  ✗ Error: {error_msg}\n")
            summaries.append({
                'paper_number': i,
                'title': paper.title,
                'abstract': paper.abstract,
                'summary': f'Error: {error_msg}',
                'status': 'error',
                'error_details': str(e)
            })
            error_count += 1
            
            # If quota error, stop processing remaining papers
            if "quota" in error_msg.lower() or "429" in str(e):
                print(f"\n⚠️  Quota exceeded. Stopping processing.")
                print(f"   Processed {i}/{len(papers)} papers before stopping.")
                break
    
    # Write summaries to file
    print(f"\n{'='*80}")
    print("Writing summaries to file...")
    print(f"{'='*80}\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PAPER ABSTRACT SUMMARIES\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total papers: {len(summaries)}\n")
        f.write(f"Successful summaries: {success_count}\n")
        f.write(f"Errors: {error_count}\n")
        f.write(f"Skipped (no abstract): {skipped_count}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        for item in summaries:
            f.write(f"{'=' * 80}\n")
            f.write(f"PAPER {item['paper_number']}")
            if 'status' in item:
                status_icon = {'success': '✓', 'error': '✗', 'skipped': '⚠'}.get(item['status'], '')
                f.write(f" [{status_icon} {item['status'].upper()}]")
            f.write(f"\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Title: {item['title']}\n\n")
            f.write(f"Original Abstract:\n{item['abstract']}\n\n")
            f.write(f"Summary:\n{item['summary']}\n\n")
            if 'error_details' in item:
                f.write(f"Error Details: {item['error_details']}\n\n")
            f.write("\n")
    
    # Print summary statistics
    print(f"✓ Summaries saved to {output_file}\n")
    print(f"{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total papers processed: {len(summaries)}")
    print(f"  ✓ Successful summaries: {success_count}")
    print(f"  ✗ Errors: {error_count}")
    print(f"  ⚠  Skipped (no abstract): {skipped_count}")
    
    if error_count > 0:
        print(f"\n⚠️  Some papers failed to summarize. Check the output file for details.")
        if "quota" in str(summaries[-1].get('error_details', '')).lower():
            print(f"💡 Tip: Your OpenAI account quota has been exceeded.")
            print(f"   Please check billing at: https://platform.openai.com/account/billing")
    
    if success_count > 0:
        print(f"\n✓ Successfully generated {success_count} summaries!")


if __name__ == "__main__":
    # Run the summarization
    summarize_all_abstracts()
