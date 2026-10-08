import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Heart, Frown, Meh, Smile, Angry } from 'lucide-react';

interface SentimentResult {
  overall: 'positive' | 'negative' | 'neutral';
  confidence: number;
  emotions: {
    joy: number;
    sadness: number;
    anger: number;
    fear: number;
    surprise: number;
  };
  keywords: string[];
}

export function SentimentAnalyzer() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const mockAnalyze = async (inputText: string): Promise<SentimentResult> => {
    // Mock analysis based on simple keyword detection
    const positiveWords = ['good', 'great', 'amazing', 'excellent', 'wonderful', 'love', 'happy', 'fantastic', 'awesome', 'brilliant'];
    const negativeWords = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'disgusting', 'worst', 'disappointing', 'sad', 'angry'];
    
    const words = inputText.toLowerCase().split(/\s+/);
    const positiveCount = words.filter(word => positiveWords.includes(word)).length;
    const negativeCount = words.filter(word => negativeWords.includes(word)).length;
    
    let overall: 'positive' | 'negative' | 'neutral';
    let confidence: number;
    
    if (positiveCount > negativeCount) {
      overall = 'positive';
      confidence = Math.min(0.9, 0.6 + (positiveCount - negativeCount) * 0.1);
    } else if (negativeCount > positiveCount) {
      overall = 'negative';
      confidence = Math.min(0.9, 0.6 + (negativeCount - positiveCount) * 0.1);
    } else {
      overall = 'neutral';
      confidence = 0.7;
    }

    return {
      overall,
      confidence,
      emotions: {
        joy: overall === 'positive' ? 75 + Math.random() * 20 : 20 + Math.random() * 30,
        sadness: overall === 'negative' ? 70 + Math.random() * 25 : 15 + Math.random() * 25,
        anger: negativeCount > 0 ? 40 + Math.random() * 40 : 10 + Math.random() * 20,
        fear: Math.random() * 30,
        surprise: Math.random() * 40,
      },
      keywords: words.filter(word => [...positiveWords, ...negativeWords].includes(word))
    };
  };

  const handleAnalyze = async () => {
    if (!text.trim()) return;
    
    setIsAnalyzing(true);
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
    const analysis = await mockAnalyze(text);
    setResult(analysis);
    setIsAnalyzing(false);
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-50';
      case 'negative': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return <Smile className="w-4 h-4" />;
      case 'negative': return <Frown className="w-4 h-4" />;
      default: return <Meh className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Heart className="w-5 h-5 text-pink-500" />
            Sentiment Analysis
          </CardTitle>
          <CardDescription>
            Analyze the emotional tone and sentiment of your text
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Enter your text here to analyze its sentiment..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="min-h-32"
          />
          <Button 
            onClick={handleAnalyze} 
            disabled={!text.trim() || isAnalyzing}
            className="w-full"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Sentiment'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getSentimentIcon(result.overall)}
                <span className="capitalize">{result.overall} Sentiment</span>
              </div>
              <Badge className={getSentimentColor(result.overall)}>
                {Math.round(result.confidence * 100)}% confident
              </Badge>
            </div>

            <div className="space-y-3">
              <h4>Emotional Breakdown</h4>
              {Object.entries(result.emotions).map(([emotion, value]) => (
                <div key={emotion} className="space-y-1">
                  <div className="flex justify-between">
                    <span className="capitalize text-sm">{emotion}</span>
                    <span className="text-sm text-muted-foreground">{Math.round(value)}%</span>
                  </div>
                  <Progress value={value} className="h-2" />
                </div>
              ))}
            </div>

            {result.keywords.length > 0 && (
              <div className="space-y-2">
                <h4>Key Sentiment Words</h4>
                <div className="flex flex-wrap gap-2">
                  {result.keywords.map((keyword, index) => (
                    <Badge key={index} variant="outline">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}