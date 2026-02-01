"""
arXiv Metrics Analyzer
Pulls and analyzes metrics for specific keywords/categories from arXiv.

Metrics:
1. Paper density: Papers per year
2. Category mapping: Number of categories linked to the keyword
3. Vocabulary coherence: Consistency of terms across papers
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from datetime import datetime
import time
import re
from typing import Dict, List, Tuple, Set


class ArxivMetricsAnalyzer:
    """Analyzer for arXiv paper metrics by keyword/category."""
    
    BASE_URL = 'http://export.arxiv.org/api/query?'
    
    def __init__(self, keyword: str, max_results: int = 1000):
        """
        Initialize the analyzer.
        
        Args:
            keyword: The arXiv category or search term (e.g., 'cond-mat.supr-con')
            max_results: Maximum number of papers to retrieve
        """
        self.keyword = keyword
        self.max_results = max_results
        self.papers = []
        
    def fetch_papers(self):
        """Fetch papers from arXiv API for the given keyword."""
        print(f"Fetching papers for keyword: {self.keyword}")
        
        # Build the query
        query = f'cat:{self.keyword}' if '.' in self.keyword else f'all:{self.keyword}'
        params = {
            'search_query': query,
            'start': 0,
            'max_results': self.max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        url = self.BASE_URL + urllib.parse.urlencode(params)
        
        try:
            with urllib.request.urlopen(url) as response:
                data = response.read()
            
            # Parse the XML response
            root = ET.fromstring(data)
            
            # Define namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}
            
            # Extract paper information
            for entry in root.findall('atom:entry', ns):
                paper = {}
                
                # Title
                title_elem = entry.find('atom:title', ns)
                paper['title'] = title_elem.text.strip() if title_elem is not None else ''
                
                # Abstract
                summary_elem = entry.find('atom:summary', ns)
                paper['abstract'] = summary_elem.text.strip() if summary_elem is not None else ''
                
                # Published date
                published_elem = entry.find('atom:published', ns)
                if published_elem is not None:
                    paper['published'] = published_elem.text.strip()
                    paper['year'] = int(published_elem.text[:4])
                
                # Categories
                categories = []
                for cat in entry.findall('atom:category', ns):
                    term = cat.get('term')
                    if term:
                        categories.append(term)
                paper['categories'] = categories
                
                self.papers.append(paper)
            
            print(f"Successfully fetched {len(self.papers)} papers")
            
        except Exception as e:
            print(f"Error fetching papers: {e}")
    
    def calculate_paper_density(self) -> Dict[int, int]:
        """
        Calculate paper density: number of papers per year.
        
        Returns:
            Dictionary mapping year to paper count
        """
        density = defaultdict(int)
        
        for paper in self.papers:
            if 'year' in paper:
                density[paper['year']] += 1
        
        # Sort by year
        density = dict(sorted(density.items()))
        
        return density
    
    def analyze_category_mapping(self) -> Dict[str, int]:
        """
        Analyze category mapping: how many categories the keyword is linked to.
        
        Returns:
            Dictionary with category statistics
        """
        all_categories = set()
        category_counts = Counter()
        
        for paper in self.papers:
            for cat in paper.get('categories', []):
                all_categories.add(cat)
                category_counts[cat] += 1
        
        results = {
            'unique_categories': len(all_categories),
            'categories': dict(category_counts.most_common()),
            'primary_category': self.keyword,
        }
        
        return results
    
    def extract_vocabulary(self, text: str) -> List[str]:
        """
        Extract meaningful vocabulary from text.
        
        Args:
            text: Input text (title or abstract)
            
        Returns:
            List of cleaned words
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters, keep letters and spaces
        text = re.sub(r'[^a-z\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter out very short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                      'that', 'these', 'those', 'we', 'us', 'our'}
        
        words = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return words
    
    def calculate_vocabulary_coherence(self, top_n: int = 50) -> Dict:
        """
        Calculate vocabulary coherence: identify consistent terms across papers.
        
        Args:
            top_n: Number of top words to analyze
            
        Returns:
            Dictionary with vocabulary statistics
        """
        all_words = []
        
        # Extract words from titles and abstracts
        for paper in self.papers:
            title_words = self.extract_vocabulary(paper.get('title', ''))
            abstract_words = self.extract_vocabulary(paper.get('abstract', ''))
            all_words.extend(title_words + abstract_words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        total_papers = len(self.papers)
        
        # Get top words
        top_words = word_counts.most_common(top_n)
        
        # Calculate coherence metrics
        results = {
            'total_unique_words': len(word_counts),
            'total_word_occurrences': len(all_words),
            'top_words': dict(top_words),
            'avg_word_frequency': len(all_words) / len(word_counts) if word_counts else 0,
        }
        
        # Calculate what percentage of papers contain each top word
        word_paper_counts = defaultdict(int)
        for paper in self.papers:
            paper_words = set(self.extract_vocabulary(
                paper.get('title', '') + ' ' + paper.get('abstract', '')
            ))
            for word in [w for w, _ in top_words]:
                if word in paper_words:
                    word_paper_counts[word] += 1
        
        # Add coherence score (percentage of papers containing top words)
        coherence_scores = {
            word: (count / total_papers * 100) 
            for word, count in word_paper_counts.items()
        }
        results['word_coherence_percentage'] = coherence_scores
        
        return results
    
    def generate_report(self):
        """Generate a comprehensive metrics report."""
        print("\n" + "="*70)
        print(f"arXiv Metrics Report for: {self.keyword}")
        print("="*70)
        
        # 1. Paper Density
        print("\n1. PAPER DENSITY (Papers/Year)")
        print("-" * 40)
        density = self.calculate_paper_density()
        
        if density:
            total_papers = sum(density.values())
            years = len(density)
            avg_per_year = total_papers / years if years > 0 else 0
            
            print(f"Total papers analyzed: {total_papers}")
            print(f"Year range: {min(density.keys())} - {max(density.keys())}")
            print(f"Average papers/year: {avg_per_year:.1f}")
            print("\nYear-by-year breakdown:")
            for year, count in sorted(density.items(), reverse=True)[:10]:
                print(f"  {year}: {count} papers")
            if len(density) > 10:
                print(f"  ... (showing latest 10 years)")
        
        # 2. Category Mapping
        print("\n2. CATEGORY MAPPING")
        print("-" * 40)
        category_mapping = self.analyze_category_mapping()
        
        print(f"Primary category: {category_mapping['primary_category']}")
        print(f"Total unique categories: {category_mapping['unique_categories']}")
        print("\nTop 10 associated categories:")
        for i, (cat, count) in enumerate(
            list(category_mapping['categories'].items())[:10], 1
        ):
            percentage = (count / len(self.papers) * 100)
            print(f"  {i}. {cat}: {count} papers ({percentage:.1f}%)")
        
        # 3. Vocabulary Coherence
        print("\n3. VOCABULARY COHERENCE")
        print("-" * 40)
        vocab = self.calculate_vocabulary_coherence(top_n=30)
        
        print(f"Total unique words: {vocab['total_unique_words']}")
        print(f"Total word occurrences: {vocab['total_word_occurrences']}")
        print(f"Average word frequency: {vocab['avg_word_frequency']:.2f}")
        
        print("\nTop 20 most frequent terms (with coherence %):")
        coherence = vocab['word_coherence_percentage']
        for i, (word, count) in enumerate(list(vocab['top_words'].items())[:20], 1):
            coh_pct = coherence.get(word, 0)
            print(f"  {i:2d}. {word:20s} - {count:4d} occurrences ({coh_pct:.1f}% of papers)")
        
        print("\n" + "="*70)


def main():
    """Main function to run the analyzer."""
    # Example usage with cond-mat.supr-con
    keyword = 'cond-mat.supr-con'
    
    print(f"Starting arXiv metrics analysis...")
    print(f"Keyword: {keyword}")
    print(f"Note: This may take a moment depending on the number of papers...\n")
    
    # Initialize analyzer
    analyzer = ArxivMetricsAnalyzer(keyword, max_results=5000)
    
    # Fetch papers
    analyzer.fetch_papers()
    
    # Add a small delay to be respectful to arXiv API
    time.sleep(1)
    
    # Generate report
    if analyzer.papers:
        analyzer.generate_report()
    else:
        print("No papers found for the given keyword.")


if __name__ == '__main__':
    main()
