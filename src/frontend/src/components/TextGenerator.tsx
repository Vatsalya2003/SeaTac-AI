import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Copy, Wand2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface GenerationOptions {
  type: 'creative' | 'professional' | 'casual' | 'technical';
  length: number;
  temperature: number;
}

export function TextGenerator() {
  const [prompt, setPrompt] = useState('');
  const [generatedText, setGeneratedText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [options, setOptions] = useState<GenerationOptions>({
    type: 'creative',
    length: 100,
    temperature: 0.7
  });

  const mockGenerate = async (inputPrompt: string, opts: GenerationOptions): Promise<string> => {
    const templates = {
      creative: [
        "In a world where imagination knows no bounds, your idea sparks a fascinating journey. The concept you've shared opens doors to endless possibilities, weaving together elements that create something truly unique and captivating.",
        "Once upon a time, in the realm of creativity, there existed a story waiting to be told. Your prompt has awakened this narrative, bringing forth characters and scenarios that dance between reality and dreams.",
        "The creative spark ignites, transforming your initial thought into a tapestry of words that flow like a gentle stream, carrying readers through landscapes of wonder and discovery."
      ],
      professional: [
        "In today's dynamic business environment, the strategic implications of your proposal warrant careful consideration. Our analysis suggests that implementing this approach could yield significant benefits while maintaining operational efficiency.",
        "Based on current market trends and industry best practices, the framework you've outlined presents a comprehensive solution that addresses key stakeholder concerns and drives measurable outcomes.",
        "The professional consensus indicates that your strategic initiative aligns with organizational objectives and demonstrates a clear understanding of contemporary business challenges."
      ],
      casual: [
        "Hey there! So I was thinking about what you mentioned, and honestly, it sounds pretty cool. Like, there's definitely something there worth exploring, you know? It's got that vibe that just makes sense.",
        "Okay, so here's the thing - your idea is actually really interesting! I can totally see where you're coming from, and it reminds me of some other stuff I've been thinking about lately.",
        "Dude, that's such a neat concept! I love how you're approaching this whole thing. It's got this fresh perspective that's totally different from the usual stuff we see."
      ],
      technical: [
        "From a technical standpoint, the implementation architecture requires careful consideration of scalability factors and system integration patterns. The proposed solution demonstrates adherence to established engineering principles while accommodating future extensibility requirements.",
        "The technical specifications outlined in your requirements document suggest a robust framework that leverages modern development paradigms and industry-standard protocols to ensure optimal performance and maintainability.",
        "Analysis of the technical feasibility indicates that the system design incorporates appropriate abstraction layers and follows established software engineering practices for enhanced modularity and code reusability."
      ]
    };

    const selectedTemplates = templates[opts.type];
    const baseText = selectedTemplates[Math.floor(Math.random() * selectedTemplates.length)];
    
    // Adjust length based on slider value
    const words = baseText.split(' ');
    const targetWords = Math.floor(opts.length * 1.5); // Convert slider value to approximate word count
    
    if (words.length > targetWords) {
      return words.slice(0, targetWords).join(' ') + '...';
    } else if (words.length < targetWords) {
      // Extend the text by repeating variations
      const extensions = [
        " Furthermore, this approach demonstrates the potential for innovative solutions that bridge traditional methodologies with contemporary thinking.",
        " Additionally, the implementation strategy offers flexibility while maintaining core functionality and user experience standards.",
        " The comprehensive nature of this solution ensures that all stakeholder requirements are addressed effectively."
      ];
      
      let extended = baseText;
      while (extended.split(' ').length < targetWords) {
        extended += extensions[Math.floor(Math.random() * extensions.length)];
      }
      
      return extended.split(' ').slice(0, targetWords).join(' ') + '.';
    }
    
    return baseText;
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setIsGenerating(true);
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    const generated = await mockGenerate(prompt, options);
    setGeneratedText(generated);
    setIsGenerating(false);
  };

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(generatedText);
    toast.success('Text copied to clipboard!');
  };

  const regenerate = () => {
    if (generatedText) {
      handleGenerate();
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wand2 className="w-5 h-5 text-purple-500" />
            AI Text Generator
          </CardTitle>
          <CardDescription>
            Generate creative content based on your prompts and preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prompt">Prompt</Label>
            <Textarea
              id="prompt"
              placeholder="Enter your prompt or topic here..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="min-h-24"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Writing Style</Label>
              <Select 
                value={options.type} 
                onValueChange={(value: any) => setOptions({...options, type: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="creative">Creative</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="casual">Casual</SelectItem>
                  <SelectItem value="technical">Technical</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Length: {options.length} words</Label>
              <Slider
                value={[options.length]}
                onValueChange={(value) => setOptions({...options, length: value[0]})}
                min={50}
                max={500}
                step={25}
                className="mt-2"
              />
            </div>

            <div className="space-y-2">
              <Label>Creativity: {options.temperature}</Label>
              <Slider
                value={[options.temperature]}
                onValueChange={(value) => setOptions({...options, temperature: value[0]})}
                min={0.1}
                max={1.0}
                step={0.1}
                className="mt-2"
              />
            </div>
          </div>

          <Button 
            onClick={handleGenerate} 
            disabled={!prompt.trim() || isGenerating}
            className="w-full"
          >
            {isGenerating ? 'Generating...' : 'Generate Text'}
          </Button>
        </CardContent>
      </Card>

      {generatedText && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Generated Content
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={regenerate}
                  disabled={isGenerating}
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={copyToClipboard}>
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-muted p-4 rounded-lg">
              <p className="whitespace-pre-wrap">{generatedText}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}