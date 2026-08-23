//+------------------------------------------------------------------+
//|                                            BlackWolf_EA.mq5       |
//|                              Copyright 2025, Black Wolf Trading    |
//+------------------------------------------------------------------+
#property copyright "Black Wolf Trading"
#property version   "2.10"
#property strict

//--- Inputs
input string   InpApiKey         = "";           // Gemini API Key
input double   InpLotSize        = 0.01;         // Lot Size
input int      InpMaxSpread      = 50;           // Max Spread (points)
input int      InpInterval       = 15;           // Check Every (minutes)
input int      InpCandles        = 50;           // Number of Candles
input ulong    InpMagicNumber    = 777001;       // Magic Number
input int      InpMinConfidence  = 60;           // Min Confidence %
input bool     InpDeleteOpposite = true;        // Close opposite on new signal

//--- Globals
string   API_KEY;
string   LAST_SIGNAL_ID = "";
datetime LAST_ANALYSIS_TIME = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   API_KEY = InpApiKey;
   
   if(StringLen(API_KEY) < 10)
     {
      Print("ERROR: Set your Gemini API Key in EA settings!");
      Alert("Black Wolf: Set API Key first!");
      return(INIT_PARAMETERS_INCORRECT);
     }
   
   EventSetTimer(InpInterval * 60);
   Print("Black Wolf EA started. Symbol: ", _Symbol, " | Interval: ", InpInterval, " min");
   Comment("\n  Black Wolf EA\n  Waiting for first analysis...\n");
   
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   }

//+------------------------------------------------------------------+
void OnTimer()
  {
   if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
      return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpread)
      return;
   
   if((int)(TimeCurrent() - LAST_ANALYSIS_TIME) < 60)
      return;
   
   Comment("\n  Black Wolf EA\n  Analyzing market...\n");
   
   string result = RunAnalysis();
   if(result == "")
     {
      Comment("\n  Black Wolf EA\n  Analysis failed. Retry next cycle...\n");
      return;
     }
   
   ProcessSignal(result);
  }

//+------------------------------------------------------------------+
string RunAnalysis()
  {
   LAST_ANALYSIS_TIME = TimeCurrent();
   
   string candleData = GetCandleData();
   if(candleData == "")
      return "";
   
   string prompt = BuildPrompt(candleData);
   string response = CallGeminiAPI(prompt);
   
   if(response == "")
      return "";
   
   return ExtractJSON(response);
  }

//+------------------------------------------------------------------+
string GetCandleData()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   
   int copied = CopyRates(_Symbol, PERIOD_M5, 0, InpCandles, rates);
   if(copied < InpCandles)
     {
      Print("ERROR: Got ", copied, " candles");
      return "";
     }
   
   string data = "XAUUSD | Timeframe: M5\n";
   data += "Current Price: " + DoubleToString(rates[0].close, 2) + "\n";
   data += "\nCandles (O/H/L/C/V):\n";
   
   for(int i = copied - 1; i >= 0; i--)
     {
      int num = copied - i;
      data += StringFormat("#%3d O:%8.2f H:%8.2f L:%8.2f C:%8.2f V:%6.0f\n",
                           num, rates[i].open, rates[i].high, rates[i].low, rates[i].close, rates[i].tick_volume);
     }
   
   return data;
  }

//+------------------------------------------------------------------+
string BuildPrompt(string candleData)
  {
   string dt = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   
   string p = "You are Black Wolf, elite gold trading AI. Analyze using SMC (Order Blocks, Liquidity, BOS, CHoCH, FVG), Risk Management (structure-based SL, liquidity TP, min 1:2 R:R), Market Sentiment, and Macro (Fed, DXY, geopolitics).\n\n";
   p += "Date: " + dt + " UTC\n\n";
   p += candleData + "\n";
   p += "Respond ONLY in exact JSON (no markdown, no code blocks):\n";
   p += "{\"signal\":\"BUY\",\"entry\":0.00,\"stop_loss\":0.00,\"tp1\":0.00,\"tp2\":0.00,\"confidence\":75,\"reasoning\":\"brief\",\"risk\":\"risk\"}\n\n";
   p += "Rules: signal = BUY/SELL/HOLD. If confidence<60 use HOLD. Use current price as entry.\n";
   
   return p;
  }

//+------------------------------------------------------------------+
string CallGeminiAPI(string prompt)
  {
   string url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=" + API_KEY;
   
   string escaped = EscapeJSON(prompt);
   string body = "{\"contents\":[{\"parts\":[{\"text\":\"" + escaped + "\"}]}],\"generationConfig\":{\"maxOutputTokens\":500,\"temperature\":0.7}}";
   
   string headers = "Content-Type: application/json\r\n";
   
   char postData[];  
   char resultData[];
   string resultHeaders;
   
   StringToCharArray(body, postData, 0, WHOLE_ARRAY, CP_UTF8);
   
   ResetLastError();
   int res = WebRequest("POST", url, headers, 5000, postData, resultData, resultHeaders);
   
   if(res == -1)
     {
      int err = GetLastError();
      Print("WebRequest ERROR ", err);
      if(err == 4060)
         Print("FIX: Tools>Options>Expert Advisors>Allow WebRequest + add: generativelanguage.googleapis.com");
      return "";
     }
   
   if(res != 200)
     {
      string s = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
      Print("HTTP ", res, ": ", StringSubstr(s, 0, 200));
      return "";
     }
   
   string resp = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
   Print("Gemini OK, len=", StringLen(resp));
   return resp;
  }

//+------------------------------------------------------------------+
string EscapeJSON(string text)
  {
   string r = text;
   StringReplace(r, "\\", "\\\\");
   StringReplace(r, "\"", "\\\"");
   StringReplace(r, "\n", "\\n");
   StringReplace(r, "\r", "\\r");
   StringReplace(r, "\t", "\\t");
   return r;
  }

//+------------------------------------------------------------------+
string ExtractJSON(string response)
  {
   // Remove markdown code blocks
   StringReplace(response, "```json", "");
   StringReplace(response, "```", "");
   
   // Find the signal JSON object
   int start = StringFind(response, "{\"signal");
   if(start < 0) start = StringFind(response, "{\" signal");
   if(start < 0) start = StringFind(response, "{\"signal\":");
   
   if(start < 0)
     {
      Print("No signal JSON found in response");
      return "";
     }
   
   // Find matching closing brace
   int depth = 0;
   int end = -1;
   for(int i = start; i < StringLen(response); i++)
     {
      ushort ch = StringGetCharacter(response, i);
      if(ch == '{') depth++;
      else if(ch == '}')
        {
         depth--;
         if(depth == 0)
           {
            end = i;
            break;
           }
        }
     }
   
   if(end > start)
      return StringSubstr(response, start, end - start + 1);
   
   return "";
  }

//+------------------------------------------------------------------+
void ProcessSignal(string signalJson)
  {
   string signal = GetJSONValue(signalJson, "signal");
   double entry   = StringToDouble(GetJSONValue(signalJson, "entry"));
   double sl      = StringToDouble(GetJSONValue(signalJson, "stop_loss"));
   double tp1     = StringToDouble(GetJSONValue(signalJson, "tp1"));
   double tp2     = StringToDouble(GetJSONValue(signalJson, "tp2"));
   int    conf    = (int)StringToDouble(GetJSONValue(signalJson, "confidence"));
   string reason  = GetJSONValue(signalJson, "reasoning");
   string risk    = GetJSONValue(signalJson, "risk");
   
   string sigId = signal + "_" + DoubleToString(entry, 2) + "_" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   
   Print("=== Black Wolf === ", signal, " | ", entry, " | SL:", sl, " | TP:", tp1, " | Conf:", conf, "%");
   Print("Reason: ", reason, " | Risk: ", risk);
   
   string c = "\n  Black Wolf EA\n";
   c += "  Signal: " + signal + " (" + IntegerToString(conf) + "%)\n";
   c += "  Entry: " + DoubleToString(entry, 2) + "\n";
   c += "  SL: " + DoubleToString(sl, 2) + "\n";
   c += "  TP1: " + DoubleToString(tp1, 2) + "\n";
   c += "  TP2: " + DoubleToString(tp2, 2) + "\n";
   Comment(c);
   
   if(signal != "BUY" && signal != "SELL")
     {
      Print("HOLD - no trade");
      return;
     }
   
   if(conf < InpMinConfidence)
     {
      Print("Confidence ", conf, "% < min ", InpMinConfidence, "%");
      return;
     }
   
   if(sigId == LAST_SIGNAL_ID)
     {
      Print("Duplicate signal");
      return;
     }
   
   if(entry <= 0 || sl <= 0 || tp1 <= 0)
     {
      Print("Invalid prices");
      return;
     }
   
   if(InpDeleteOpposite)
      DeleteOppositePositions(signal);
   
   if(ExecuteTrade(signal, sl, tp2 > 0 ? tp2 : tp1))
     {
      LAST_SIGNAL_ID = sigId;
      Alert("Black Wolf: ", signal, " @ ", DoubleToString(entry, 2),
            " SL:", DoubleToString(sl, 2), " TP:", DoubleToString(tp1, 2));
     }
  }

//+------------------------------------------------------------------+
bool ExecuteTrade(string signal, double sl, double tp)
  {
   MqlTradeRequest request;
   MqlTradeResult  result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   if(signal == "BUY")
     {
      request.type  = ORDER_TYPE_BUY;
      request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
     }
   else
     {
      request.type  = ORDER_TYPE_SELL;
      request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
     }
   
   request.action   = TRADE_ACTION_DEAL;
   request.symbol   = _Symbol;
   request.volume   = InpLotSize;
   request.sl       = sl;
   request.tp       = tp;
   request.deviation = 10;
   request.magic    = InpMagicNumber;
   request.comment  = "BlackWolf";
   
   ResetLastError();
   bool sent = OrderSend(request, result);
   
   if(!sent || result.retcode != TRADE_RETCODE_DONE)
     {
      Print("Order FAILED. Error: ", GetLastError(), " RetCode: ", result.retcode, " - ", result.comment);
      Alert("Black Wolf: Order failed - ", result.comment);
      return false;
     }
   
   Print("Order OPEN! Ticket: ", result.order, " Price: ", result.price, " Vol: ", result.volume);
   return true;
  }

//+------------------------------------------------------------------+
void DeleteOppositePositions(string newSignal)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      long posType = PositionGetInteger(POSITION_TYPE);
      bool isOpposite = (newSignal == "BUY" && posType == POSITION_TYPE_SELL) ||
                        (newSignal == "SELL" && posType == POSITION_TYPE_BUY);
      
      if(!isOpposite) continue;
      
      MqlTradeRequest request;
      MqlTradeResult  result;
      ZeroMemory(request);
      ZeroMemory(result);
      
      request.action   = TRADE_ACTION_DEAL;
      request.symbol   = _Symbol;
      request.volume   = PositionGetDouble(POSITION_VOLUME);
      request.deviation = 10;
      request.magic    = InpMagicNumber;
      request.position  = ticket;
      request.comment  = "BlackWolf Close";
      
      if(posType == POSITION_TYPE_BUY)
        {
         request.type  = ORDER_TYPE_SELL;
         request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
        }
      else
        {
         request.type  = ORDER_TYPE_BUY;
         request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        }
      
      if(OrderSend(request, result))
         Print("Closed opposite #", ticket);
      else
         Print("Failed to close #", ticket);
     }
  }

//+------------------------------------------------------------------+
string GetJSONValue(string json, string key)
  {
   string searchKey = "\"" + key + "\":";
   int start = StringFind(json, searchKey);
   
   if(start < 0)
      return "";
   
   start += StringLen(searchKey);
   
   // Skip spaces
   while(start < StringLen(json) && StringGetCharacter(json, start) == ' ')
      start++;
   
   if(start >= StringLen(json))
      return "";
   
   // String value
   if(StringGetCharacter(json, start) == '"')
     {
      start++;
      int end = StringFind(json, "\"", start);
      if(end > start)
         return StringSubstr(json, start, end - start);
      return "";
     }
   
   // Numeric value
   int end = start;
   while(end < StringLen(json))
     {
      ushort ch = StringGetCharacter(json, end);
      if((ch >= '0' && ch <= '9') || ch == '.' || ch == '-' || ch == '+')
         end++;
      else
         break;
     }
   
   if(end > start)
      return StringSubstr(json, start, end - start);
   
   return "";
  }
//+------------------------------------------------------------------+