import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Hash, TrendingUp, Eye, Copy } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface Keyword {
  word: string;
  frequency: number;
  relevance: number;
  category: 'entity' | 'concept' | 'action' | 'descriptor';
}

interface ExtractionResult {
  keywords: Keyword[];
  entities: string[];
  topics: string[];
  sentiment: 'positive' | 'negative' | 'neutral';
  complexity: number;
}

interface ExtractionOptions {
  maxKeywords: number;
  minLength: number;
  includeEntities: boolean;
  filterCommon: boolean;
}

export function KeywordExtractor() {
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [options, setOptions] = useState<ExtractionOptions>({
    maxKeywords: 10,
    minLength: 3,
    includeEntities: true,
    filterCommon: true
  });

  const commonWords = new Set([
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with',
    'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up',
    'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time',
    'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could',
    'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think',
    'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even',
    'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
  ]);

  const mockExtract = async (text: string, opts: ExtractionOptions): Promise<ExtractionResult> => {
    const words = text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length >= opts.minLength);

    // Filter common words if option is enabled
    const filteredWords = opts.filterCommon 
      ? words.filter(word => !commonWords.has(word))
      : words;

    // Count frequency
    const frequency: Record<string, number> = {};
    filteredWords.forEach(word => {
      frequency[word] = (frequency[word] || 0) + 1;
    });

    // Create keywords with mock relevance scores
    const keywords: Keyword[] = Object.entries(frequency)
      .sort(([,a], [,b]) => b - a)
      .slice(0, opts.maxKeywords)
      .map(([word, freq]) => ({
        word,
        frequency: freq,
        relevance: Math.min(95, 60 + (freq * 5) + Math.random() * 20),
        category: Math.random() > 0.7 ? 'entity' : 
                 Math.random() > 0.5 ? 'concept' : 
                 Math.random() > 0.3 ? 'action' : 'descriptor'
      }));

    // Mock entity extraction
    const entities = opts.includeEntities ? [
      'Technology', 'Innovation', 'Development', 'Analysis', 'Research'
    ].slice(0, Math.ceil(keywords.length / 3)) : [];

    // Mock topic extraction
    const topics = [
      'Digital Transformation',
      'Data Analytics',
      'User Experience',
      'Business Strategy',
      'Technical Implementation'
    ].slice(0, Math.ceil(keywords.length / 2));

    // Mock sentiment analysis
    const positiveWords = keywords.filter(k => 
      ['good', 'great', 'excellent', 'amazing', 'wonderful', 'success', 'improve', 'benefit'].includes(k.word)
    ).length;
    const negativeWords = keywords.filter(k => 
      ['bad', 'poor', 'terrible', 'problem', 'issue', 'fail', 'difficult', 'challenge'].includes(k.word)
    ).length;
    
    const sentiment = positiveWords > negativeWords ? 'positive' : 
                     negativeWords > positiveWords ? 'negative' : 'neutral';

    // Mock complexity score
    const uniqueWords = new Set(words).size;
    const avgWordLength = words.reduce((sum, word) => sum + word.length, 0) / words.length;
    const complexity = Math.min(100, (uniqueWords / words.length) * 100 + avgWordLength * 5);

    return {
      keywords,
      entities,
      topics,
      sentiment,
      complexity
    };
  };

  const handleExtract = async () => {
    if (!inputText.trim()) return;
    
    setIsExtracting(true);
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
    const extraction = await mockExtract(inputText, options);
    setResult(extraction);
    setIsExtracting(false);
  };

  const copyKeywords = async () => {
    if (result) {
      const keywordsList = result.keywords.map(k => k.word).join(', ');
      await navigator.clipboard.writeText(keywordsList);
      toast.success('Keywords copied to clipboard!');
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'entity': return 'bg-blue-100 text-blue-800';
      case 'concept': return 'bg-green-100 text-green-800';
      case 'action': return 'bg-purple-100 text-purple-800';
      case 'descriptor': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600';
      case 'negative': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-emerald-500" />
            Keyword Extractor
          </CardTitle>
          <CardDescription>
            Extract key terms, entities, and topics from your text with AI analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="input-text">Text to Analyze</Label>
            <Textarea
              id="input-text"
              placeholder="Enter your text here to extract keywords and key information..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="min-h-32"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Max Keywords</Label>
              <Select 
                value={options.maxKeywords.toString()} 
                onValueChange={(value) => setOptions({...options, maxKeywords: parseInt(value)})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5 keywords</SelectItem>
                  <SelectItem value="10">10 keywords</SelectItem>
                  <SelectItem value="15">15 keywords</SelectItem>
                  <SelectItem value="20">20 keywords</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Min Length</Label>
              <Select 
                value={options.minLength.toString()} 
                onValueChange={(value) => setOptions({...options, minLength: parseInt(value)})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2">2+ letters</SelectItem>
                  <SelectItem value="3">3+ letters</SelectItem>
                  <SelectItem value="4">4+ letters</SelectItem>
                  <SelectItem value="5">5+ letters</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2 mt-6">
              <input
                type="checkbox"
                id="entities"
                checked={options.includeEntities}
                onChange={(e) => setOptions({...options, includeEntities: e.target.checked})}
                className="rounded"
              />
              <Label htmlFor="entities" className="text-sm">Include entities</Label>
            </div>

            <div className="flex items-center space-x-2 mt-6">
              <input
                type="checkbox"
                id="filter"
                checked={options.filterCommon}
                onChange={(e) => setOptions({...options, filterCommon: e.target.checked})}
                className="rounded"
              />
              <Label htmlFor="filter" className="text-sm">Filter common words</Label>
            </div>
          </div>

          <Button 
            onClick={handleExtract} 
            disabled={!inputText.trim() || isExtracting}
            className="w-full"
          >
            {isExtracting ? 'Extracting...' : 'Extract Keywords'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Analysis Overview
                </span>
                <Button variant="outline" size="sm" onClick={copyKeywords}>
                  <Copy className="w-4 h-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">{result.keywords.length}</div>
                  <div className="text-sm text-muted-foreground">Keywords Found</div>
                </div>
                <div className="text-center">
                  <div className={`text-2xl font-bold ${getSentimentColor(result.sentiment)}`}>
                    {result.sentiment.charAt(0).toUpperCase() + result.sentiment.slice(1)}
                  </div>
                  <div className="text-sm text-muted-foreground">Overall Sentiment</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{Math.round(result.complexity)}</div>
                  <div className="text-sm text-muted-foreground">Complexity Score</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Keywords by Relevance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {result.keywords.map((keyword, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge className={getCategoryColor(keyword.category)}>
                          {keyword.category}
                        </Badge>
                        <span className="font-medium">{keyword.word}</span>
                        <Badge variant="outline">
                          {keyword.frequency}x
                        </Badge>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {Math.round(keyword.relevance)}%
                      </span>
                    </div>
                    <Progress value={keyword.relevance} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {result.entities.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    Named Entities
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {result.entities.map((entity, index) => (
                      <Badge key={index} variant="secondary">
                        {entity}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Topic Clusters</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {result.topics.map((topic, index) => (
                    <Badge key={index} variant="outline" className="bg-indigo-50 text-indigo-700">
                      {topic}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}