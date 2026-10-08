import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Badge } from './ui/badge';
import { FileText, Copy, BarChart3 } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface SummaryResult {
  summary: string;
  keyPoints: string[];
  originalLength: number;
  summaryLength: number;
  compressionRatio: number;
  readingTime: number;
}

interface SummaryOptions {
  style: 'bullet' | 'paragraph' | 'abstract';
  length: 'short' | 'medium' | 'long';
  focus: 'general' | 'key-points' | 'conclusion';
}

export function TextSummarizer() {
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState<SummaryResult | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [options, setOptions] = useState<SummaryOptions>({
    style: 'paragraph',
    length: 'medium',
    focus: 'general'
  });

  const mockSummarize = async (text: string, opts: SummaryOptions): Promise<SummaryResult> => {
    const words = text.split(/\s+/).filter(word => word.length > 0);
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    
    // Mock key point extraction
    const keyPoints = [
      "The text discusses important concepts and ideas",
      "Several key arguments and supporting evidence are presented",
      "The author makes significant points about the topic",
      "Multiple perspectives and considerations are explored",
      "Conclusions and implications are drawn from the analysis"
    ].slice(0, Math.min(5, Math.ceil(sentences.length / 3)));

    // Generate summary based on style and length
    let summary = '';
    const lengthMultiplier = opts.length === 'short' ? 0.2 : opts.length === 'medium' ? 0.4 : 0.6;
    const targetLength = Math.max(50, Math.floor(words.length * lengthMultiplier));

    if (opts.style === 'bullet') {
      summary = keyPoints.map(point => `• ${point}`).join('\n');
    } else if (opts.style === 'abstract') {
      summary = `Abstract: This text presents a comprehensive analysis of the subject matter. ${keyPoints[0]}. The discussion encompasses various aspects and provides detailed insights. ${keyPoints[1] || 'Additional considerations are explored throughout the content.'} The findings suggest important implications for understanding the topic.`;
    } else {
      // Paragraph style
      const focusIntros = {
        general: "This text provides a comprehensive overview of",
        'key-points': "The main points discussed in this text include",
        conclusion: "The primary conclusions drawn from this text are"
      };
      
      summary = `${focusIntros[opts.focus]} the subject matter. ${keyPoints.slice(0, 2).join('. ')}. The analysis presents valuable insights and considerations that contribute to our understanding of the topic.`;
    }

    // Adjust summary length
    const summaryWords = summary.split(/\s+/);
    if (summaryWords.length > targetLength) {
      summary = summaryWords.slice(0, targetLength).join(' ') + '...';
    }

    const summaryLength = summary.split(/\s+/).length;
    const compressionRatio = ((words.length - summaryLength) / words.length) * 100;

    return {
      summary,
      keyPoints,
      originalLength: words.length,
      summaryLength,
      compressionRatio,
      readingTime: Math.ceil(words.length / 200) // Average reading speed
    };
  };

  const handleSummarize = async () => {
    if (!inputText.trim()) return;
    
    setIsSummarizing(true);
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    const summary = await mockSummarize(inputText, options);
    setResult(summary);
    setIsSummarizing(false);
  };

  const copyToClipboard = async () => {
    if (result) {
      await navigator.clipboard.writeText(result.summary);
      toast.success('Summary copied to clipboard!');
    }
  };

  const getCompressionColor = (ratio: number) => {
    if (ratio >= 70) return 'text-green-600 bg-green-50';
    if (ratio >= 50) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-500" />
            Text Summarizer
          </CardTitle>
          <CardDescription>
            Create concise summaries of long texts with AI-powered analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="input-text">Text to Summarize</Label>
            <Textarea
              id="input-text"
              placeholder="Paste your long text here to generate a summary..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="min-h-40"
            />
            {inputText && (
              <div className="flex gap-4 text-sm text-muted-foreground">
                <span>{inputText.split(/\s+/).filter(w => w.length > 0).length} words</span>
                <span>{inputText.split(/[.!?]+/).filter(s => s.trim().length > 0).length} sentences</span>
                <span>~{Math.ceil(inputText.split(/\s+/).length / 200)} min read</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Summary Style</Label>
              <Select 
                value={options.style} 
                onValueChange={(value: any) => setOptions({...options, style: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paragraph">Paragraph</SelectItem>
                  <SelectItem value="bullet">Bullet Points</SelectItem>
                  <SelectItem value="abstract">Abstract</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Summary Length</Label>
              <Select 
                value={options.length} 
                onValueChange={(value: any) => setOptions({...options, length: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="short">Short (20%)</SelectItem>
                  <SelectItem value="medium">Medium (40%)</SelectItem>
                  <SelectItem value="long">Long (60%)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Focus Area</Label>
              <Select 
                value={options.focus} 
                onValueChange={(value: any) => setOptions({...options, focus: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General Overview</SelectItem>
                  <SelectItem value="key-points">Key Points</SelectItem>
                  <SelectItem value="conclusion">Conclusions</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button 
            onClick={handleSummarize} 
            disabled={!inputText.trim() || isSummarizing}
            className="w-full"
          >
            {isSummarizing ? 'Summarizing...' : 'Generate Summary'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Summary Results
              <Button variant="outline" size="sm" onClick={copyToClipboard}>
                <Copy className="w-4 h-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">{result.originalLength}</div>
                <div className="text-sm text-muted-foreground">Original Words</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{result.summaryLength}</div>
                <div className="text-sm text-muted-foreground">Summary Words</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{Math.round(result.compressionRatio)}%</div>
                <div className="text-sm text-muted-foreground">Compression</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{result.readingTime}</div>
                <div className="text-sm text-muted-foreground">Min Read</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4>Summary</h4>
                <Badge className={getCompressionColor(result.compressionRatio)}>
                  {Math.round(result.compressionRatio)}% shorter
                </Badge>
              </div>
              <div className="bg-muted p-4 rounded-lg">
                <p className="whitespace-pre-wrap">{result.summary}</p>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Key Points Extracted
              </h4>
              <ul className="space-y-2">
                {result.keyPoints.map((point, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <Badge variant="outline" className="mt-0.5 text-xs">
                      {index + 1}
                    </Badge>
                    <span className="text-sm">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}