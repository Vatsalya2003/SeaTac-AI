import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { ArrowRightLeft, Globe, Copy, Volume2 } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface Language {
  code: string;
  name: string;
  flag: string;
}

const languages: Language[] = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'it', name: 'Italian', flag: '🇮🇹' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
  { code: 'ru', name: 'Russian', flag: '🇷🇺' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
  { code: 'hi', name: 'Hindi', flag: '🇮🇳' }
];

export function TextTranslator() {
  const [sourceText, setSourceText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('es');
  const [isTranslating, setIsTranslating] = useState(false);
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null);

  const mockTranslations: Record<string, Record<string, string>> = {
    'Hello, how are you?': {
      es: 'Hola, ¿cómo estás?',
      fr: 'Bonjour, comment allez-vous?',
      de: 'Hallo, wie geht es dir?',
      it: 'Ciao, come stai?',
      pt: 'Olá, como está?',
      ru: 'Привет, как дела?',
      ja: 'こんにちは、元気ですか？',
      ko: '안녕하세요, 어떻게 지내세요?',
      zh: '你好，你好吗？',
      ar: 'مرحبا، كيف حالك؟',
      hi: 'नमस्ते, आप कैसे हैं?'
    },
    'Good morning': {
      es: 'Buenos días',
      fr: 'Bonjour',
      de: 'Guten Morgen',
      it: 'Buongiorno',
      pt: 'Bom dia',
      ru: 'Доброе утро',
      ja: 'おはようございます',
      ko: '좋은 아침',
      zh: '早上好',
      ar: 'صباح الخير',
      hi: 'सुप्रभात'
    },
    'Thank you very much': {
      es: 'Muchas gracias',
      fr: 'Merci beaucoup',
      de: 'Vielen Dank',
      it: 'Grazie mille',
      pt: 'Muito obrigado',
      ru: 'Большое спасибо',
      ja: 'どうもありがとうございます',
      ko: '정말 고맙습니다',
      zh: '非常感谢',
      ar: 'شكرا جزيلا',
      hi: 'बहुत धन्यवाद'
    }
  };

  const mockTranslate = async (text: string, from: string, to: string): Promise<string> => {
    // Check for exact matches first
    const exactMatch = mockTranslations[text]?.[to];
    if (exactMatch) return exactMatch;

    // Generate mock translation based on target language patterns
    const patterns: Record<string, string> = {
      es: 'Esta es una traducción al español de: ',
      fr: 'Ceci est une traduction française de: ',
      de: 'Dies ist eine deutsche Übersetzung von: ',
      it: 'Questa è una traduzione italiana di: ',
      pt: 'Esta é uma tradução para o português de: ',
      ru: 'Это русский перевод: ',
      ja: 'これは日本語の翻訳です：',
      ko: '이것은 한국어 번역입니다: ',
      zh: '这是中文翻译：',
      ar: 'هذه ترجمة عربية لـ: ',
      hi: 'यह हिंदी अनुवाद है: '
    };

    const pattern = patterns[to] || `[Translation to ${to}]: `;
    return pattern + text;
  };

  const detectLanguage = (text: string): string => {
    // Simple mock language detection
    if (/[¿¡ñáéíóú]/.test(text)) return 'es';
    if (/[àâäéèêëîïôöùûüÿç]/.test(text)) return 'fr';
    if (/[äöüß]/.test(text)) return 'de';
    if (/[àèìòù]/.test(text)) return 'it';
    if (/[ãõáéíóúâêôç]/.test(text)) return 'pt';
    if (/[а-я]/.test(text)) return 'ru';
    if (/[ひらがなカタカナ]/.test(text)) return 'ja';
    if (/[가-힣]/.test(text)) return 'ko';
    if (/[一-龯]/.test(text)) return 'zh';
    if (/[ا-ي]/.test(text)) return 'ar';
    if (/[अ-ह]/.test(text)) return 'hi';
    return 'en';
  };

  const handleTranslate = async () => {
    if (!sourceText.trim()) return;
    
    setIsTranslating(true);
    
    // Mock language detection
    const detected = detectLanguage(sourceText);
    if (detected !== sourceLang) {
      setDetectedLanguage(detected);
    }
    
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
    const translated = await mockTranslate(sourceText, sourceLang, targetLang);
    setTranslatedText(translated);
    setIsTranslating(false);
  };

  const swapLanguages = () => {
    const tempLang = sourceLang;
    setSourceLang(targetLang);
    setTargetLang(tempLang);
    
    if (translatedText) {
      setSourceText(translatedText);
      setTranslatedText(sourceText);
    }
  };

  const copyTranslation = async () => {
    await navigator.clipboard.writeText(translatedText);
    toast.success('Translation copied to clipboard!');
  };

  const speakText = (text: string, lang: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      speechSynthesis.speak(utterance);
    } else {
      toast.error('Speech synthesis not supported in this browser');
    }
  };

  const getLanguageFlag = (code: string) => {
    return languages.find(lang => lang.code === code)?.flag || '🌐';
  };

  const getLanguageName = (code: string) => {
    return languages.find(lang => lang.code === code)?.name || code;
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-500" />
            AI Translator
          </CardTitle>
          <CardDescription>
            Translate text between multiple languages with AI-powered accuracy
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Label>From</Label>
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.flag} {lang.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <Button 
              variant="outline" 
              size="sm" 
              onClick={swapLanguages}
              className="mt-6"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </Button>
            
            <div className="flex-1">
              <Label>To</Label>
              <Select value={targetLang} onValueChange={setTargetLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.flag} {lang.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Source Text</Label>
                {sourceText && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => speakText(sourceText, sourceLang)}
                  >
                    <Volume2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
              <Textarea
                placeholder="Enter text to translate..."
                value={sourceText}
                onChange={(e) => setSourceText(e.target.value)}
                className="min-h-32"
              />
              {detectedLanguage && detectedLanguage !== sourceLang && (
                <p className="text-sm text-muted-foreground">
                  Detected language: {getLanguageFlag(detectedLanguage)} {getLanguageName(detectedLanguage)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Translation</Label>
                {translatedText && (
                  <div className="flex gap-1">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => speakText(translatedText, targetLang)}
                    >
                      <Volume2 className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={copyTranslation}>
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
              <div className="min-h-32 p-3 bg-muted rounded-md border">
                {isTranslating ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-muted-foreground">Translating...</div>
                  </div>
                ) : translatedText ? (
                  <p className="whitespace-pre-wrap">{translatedText}</p>
                ) : (
                  <div className="text-muted-foreground">Translation will appear here...</div>
                )}
              </div>
            </div>
          </div>

          <Button 
            onClick={handleTranslate} 
            disabled={!sourceText.trim() || isTranslating}
            className="w-full"
          >
            {isTranslating ? 'Translating...' : 'Translate'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}