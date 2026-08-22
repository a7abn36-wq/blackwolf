//+------------------------------------------------------------------+
//|                                            BlackWolf_EA.mq5       |
//|                              Copyright 2025, Black Wolf Trading    |
//|                                             https://blackwolf.ai   |
//+------------------------------------------------------------------+
#property copyright "Black Wolf Trading"
#property link      "https://blackwolf.ai"
#property version   "2.00"
#property strict

//--- Inputs
input string   InpApiKey      = "";           // Gemini API Key
input double   InpLotSize     = 0.01;         // Lot Size
input int      InpMaxSpread   = 50;           // Max Spread (points)
input int      InpInterval    = 15;           // Check Every (minutes)
input int      InpCandles     = 50;           // Number of Candles
input ulong    InpMagicNumber = 777001;       // Magic Number
input int      InpMinConfidence = 60;         // Min Confidence %
input bool     InpDeleteOpposite = true;      // Close opposite on new signal

//--- Globals
string   API_KEY;
string   LAST_SIGNAL_ID = "";
datetime LAST_ANALYSIS_TIME = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
  {
   API_KEY = InpApiKey;
   
   if(StringLen(API_KEY) < 10)
     {
      Print("ERROR: Please set your Gemini API Key in EA settings!");
      Alert("Black Wolf: Set API Key first!");
      return(INIT_PARAMETERS_INCORRECT);
     }
   
   EventSetTimer(InpInterval * 60);
   Print("Black Wolf EA initialized. Checking every ", InpInterval, " minutes.");
   Print("Symbol: ", _Symbol, " | Lot: ", InpLotSize, " | Candles: ", InpCandles);
   
   Comment("\n\n  Black Wolf EA\n  Waiting for first analysis...\n");
   
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   Print("Black Wolf EA stopped.");
  }

//+------------------------------------------------------------------+
//| Timer function - main analysis loop                                 |
//+------------------------------------------------------------------+
void OnTimer()
  {
   if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
      return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpread)
     {
      Print("Spread too high: ", spread, " > ", InpMaxSpread);
      return;
     }
   
   if((int)(TimeCurrent() - LAST_ANALYSIS_TIME) < 60)
      return;
   
   Comment("\n\n  Black Wolf EA\n  Analyzing market...\n");
   
   string result = RunAnalysis();
   
   if(result == "")
     {
      Comment("\n\n  Black Wolf EA\n  Analysis failed. Retrying next interval...\n");
      return;
     }
   
   ProcessSignal(result);
  }

//+------------------------------------------------------------------+
//| Run AI Analysis                                                    |
//+------------------------------------------------------------------+
string RunAnalysis()
  {
   LAST_ANALYSIS_TIME = TimeCurrent();
   
   string candleData = GetCandleData();
   if(candleData == "")
     {
      Print("ERROR: Could not get candle data");
      return "";
     }
   
   string prompt = BuildPrompt(candleData);
   string response = CallGeminiAPI(prompt);
   
   if(response == "")
     {
      Print("ERROR: Gemini API call failed");
      return "";
     }
   
   string signalJson = ExtractJSON(response);
   if(signalJson == "")
     {
      Print("ERROR: Could not extract signal JSON");
      Print("Response: ", StringSubstr(response, 0, 200));
      return "";
     }
   
   return signalJson;
  }

//+------------------------------------------------------------------+
//| Get candle data as text                                             |
//+------------------------------------------------------------------+
string GetCandleData()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   
   int copied = CopyRates(_Symbol, PERIOD_M5, 0, InpCandles, rates);
   if(copied < InpCandles)
     {
      Print("ERROR: Only got ", copied, " candles");
      return "";
     }
   
   string data = "XAUUSD | Entry Timeframe: M5 | Analysis Timeframe: H1+\n";
   data += "Current Price: " + DoubleToString(rates[0].close, 2) + "\n";
   data += "\nRecent Candles (most recent last, O/H/L/C/V):\n";
   
   for(int i = copied - 1; i >= 0; i--)
     {
      int num = copied - i;
      data += StringFormat("#%3d  O:%8.2f  H:%8.2f  L:%8.2f  C:%8.2f  V:%6.0f\n",
                           num, rates[i].open, rates[i].high, rates[i].low, rates[i].close, rates[i].tick_volume);
     }
   
   return data;
  }

//+------------------------------------------------------------------+
//| Build the analysis prompt                                          |
//+------------------------------------------------------------------+
string BuildPrompt(string candleData)
  {
   string datetimeStr = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   
   string prompt = "You are Black Wolf, an elite multi-disciplinary gold (XAUUSD) trading AI.\n\n";
   prompt += "Analyze the following M5 candle data using ALL of these approaches:\n\n";
   prompt += "1. SMC TECHNICAL: Order Blocks, Liquidity Pools, BOS, CHoCH, FVG, Supply/Demand zones\n";
   prompt += "2. RISK MANAGEMENT: SL based on structure (not arbitrary), TP at liquidity targets, minimum 1:2 R:R\n";
   prompt += "3. MARKET: Sentiment (risk-on vs risk-off), momentum, smart money positioning\n";
   prompt += "4. MACRO: Fed policy direction, DXY impact, geopolitical risks, seasonal patterns\n\n";
   prompt += "Current date/time: " + datetimeStr + " UTC\n\n";
   prompt += candleData + "\n";
   prompt += "Respond ONLY in this exact JSON format (no markdown, no extra text, no code blocks):\n";
   prompt += "{\"signal\":\"BUY\",\"entry\":0.00,\"stop_loss\":0.00,\"tp1\":0.00,\"tp2\":0.00,\"confidence\":75,\"reasoning\":\"brief reason\",\"risk\":\"key risk\"}\n\n";
   prompt += "Rules:\n";
   prompt += "- signal must be exactly BUY, SELL, or HOLD\n";
   prompt += "- If confidence < 60, output HOLD\n";
   prompt += "- SL must be based on market structure (order blocks, swing points)\n";
   prompt += "- TP should target liquidity pools\n";
   prompt += "- Use the current price as entry\n";
   
   return prompt;
  }

//+------------------------------------------------------------------+
//| Call Gemini API                                                    |
//+------------------------------------------------------------------+
string CallGeminiAPI(string prompt)
  {
   string url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=" + API_KEY;
   
   string escapedPrompt = EscapeJSON(prompt);
   string jsonBody = "{\"contents\":[{\"parts\":[{\"text\":\"" + escapedPrompt + "\"}]}],\"generationConfig\":{\"maxOutputTokens\":500,\"temperature\":0.7}}";
   
   string headers = "Content-Type: application/json\r\n";
   
   char   postData[];  
   char   resultData[];
   string resultHeaders;
   
   StringToCharArray(jsonBody, postData, 0, WHOLE_ARRAY, CP_UTF8);
   
   ResetLastError();
   int res = WebRequest("POST", url, headers, 5000, postData, resultData, resultHeaders);
   
   if(res == -1)
     {
      int err = GetLastError();
      Print("WebRequest failed. Error: ", err);
      if(err == 4060)
         Print("FIX: Tools > Options > Expert Advisors > Allow WebRequest\n"
               "Add URL: https://generativelanguage.googleapis.com");
      return "";
     }
   
   if(res != 200)
     {
      Print("API returned HTTP ", res);
      string resultStr = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
      Print("Response: ", StringSubstr(resultStr, 0, 300));
      return "";
     }
   
   string resultStr = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
   return resultStr;
  }

//+------------------------------------------------------------------+
//| Escape string for JSON                                              |
//+------------------------------------------------------------------+
string EscapeJSON(string text)
  {
   string result = text;
   StringReplace(result, "\\", "\\\\");
   StringReplace(result, "\"", "\\\"");
   StringReplace(result, "\n", "\\n");
   StringReplace(result, "\r", "\\r");
   StringReplace(result, "\t", "\\t");
   return result;
  }

//+------------------------------------------------------------------+
//| Extract JSON signal from Gemini response                            |
//+------------------------------------------------------------------+
string ExtractJSON(string response)
  {
   // Try MQL5 JSON parser
   if(JsonParse(response) > 0)
     {
      string textValue = JsonGetString(response, "candidates[0].content.parts[0].text");
      
      if(StringLen(textValue) > 0)
        {
         string cleanText = textValue;
         StringReplace(cleanText, "```json", "");
         StringReplace(cleanText, "```", "");
         StringTrimLeft(cleanText);
         StringTrimRight(cleanText);
         
         if(StringGetCharacter(cleanText, 0) == '{')
            return cleanText;
         
         int start = StringFind(cleanText, "{\"");
         if(start < 0) start = StringFind(cleanText, "{");
         if(start >= 0)
           {
            int end = StringFind(cleanText, "}", start);
            if(end > start)
               return StringSubstr(cleanText, start, end - start + 1);
           }
        }
     }
   
   // Fallback: manual search
   int jsonStart = StringFind(response, "{\"signal");
   if(jsonStart < 0) jsonStart = StringFind(response, "{\"signal\":");
   
   if(jsonStart >= 0)
     {
      int jsonEnd = StringFind(response, "}", jsonStart);
      if(jsonEnd > jsonStart)
         return StringSubstr(response, jsonStart, jsonEnd - jsonStart + 1);
     }
   
   return "";
  }

//+------------------------------------------------------------------+
//| Process signal and execute trade                                    |
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
   
   string signalId = signal + "_" + DoubleToString(entry, 2) + "_" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   
   Print("=== Black Wolf Signal ===");
   Print("Signal: ", signal, " | Entry: ", entry, " | SL: ", sl);
   Print("TP1: ", tp1, " | TP2: ", tp2, " | Confidence: ", conf, "%");
   Print("Reasoning: ", reason);
   Print("========================");
   
   string commentText = "\n  Black Wolf EA\n";
   commentText += "  Signal: " + signal + " (" + IntegerToString(conf) + "%)\n";
   commentText += "  Entry: " + DoubleToString(entry, 2) + "\n";
   commentText += "  SL: " + DoubleToString(sl, 2) + "\n";
   commentText += "  TP1: " + DoubleToString(tp1, 2) + "\n";
   commentText += "  TP2: " + DoubleToString(tp2, 2) + "\n";
   commentText += "  Reason: " + reason + "\n";
   Comment(commentText);
   
   if(signal != "BUY" && signal != "SELL")
     {
      Print("Signal is HOLD - no trade");
      Alert("Black Wolf: HOLD");
      return;
     }
   
   if(conf < InpMinConfidence)
     {
      Print("Confidence ", conf, "% below min ", InpMinConfidence, "%");
      return;
     }
   
   if(signalId == LAST_SIGNAL_ID)
     {
      Print("Duplicate signal, skipping");
      return;
     }
   
   if(entry <= 0 || sl <= 0 || tp1 <= 0)
     {
      Print("Invalid prices");
      return;
     }
   
   if(InpDeleteOpposite)
      DeleteOppositePositions(signal);
   
   bool success = ExecuteTrade(signal, entry, sl, tp1, tp2);
   
   if(success)
     {
      LAST_SIGNAL_ID = signalId;
      Alert("Black Wolf: ", signal, " executed! Entry: ", DoubleToString(entry, 2));
     }
  }

//+------------------------------------------------------------------+
//| Execute trade                                                       |
//+------------------------------------------------------------------+
bool ExecuteTrade(string signal, double entry, double sl, double tp1, double tp2)
  {
   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};
   
   double mainTP = tp2 > 0 ? tp2 : tp1;
   
   if(signal == "BUY")
     {
      request.type    = ORDER_TYPE_BUY;
      request.price   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      request.sl      = sl;
      request.tp      = mainTP;
     }
   else
     {
      request.type    = ORDER_TYPE_SELL;
      request.price   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      request.sl      = sl;
      request.tp      = mainTP;
     }
   
   request.action   = TRADE_ACTION_DEAL;
   request.symbol   = _Symbol;
   request.volume   = InpLotSize;
   request.deviation = 10;
   request.magic    = InpMagicNumber;
   StringToCharArray("BlackWolf", request.comment, 0, WHOLE_ARRAY, CP_UTF8);
   
   ResetLastError();
   bool sent = OrderSend(request, result);
   
   if(!sent || result.retcode != TRADE_RETCODE_DONE)
     {
      Print("OrderSend failed. Error: ", GetLastError(), " RetCode: ", result.retcode);
      Print("Comment: ", result.comment);
      Alert("Black Wolf: Order failed - ", result.comment);
      return false;
     }
   
   Print("Order executed! Ticket: ", result.order, " Price: ", result.price);
   return true;
  }

//+------------------------------------------------------------------+
//| Delete opposite positions                                           |
//+------------------------------------------------------------------+
void DeleteOppositePositions(string newSignal)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      long posType = PositionGetInteger(POSITION_TYPE);
      
      if((newSignal == "BUY" && posType == POSITION_TYPE_SELL) ||
         (newSignal == "SELL" && posType == POSITION_TYPE_BUY))
        {
         MqlTradeRequest request = {};
         MqlTradeResult  result  = {};
         
         request.action   = TRADE_ACTION_DEAL;
         request.symbol   = _Symbol;
         request.volume   = PositionGetDouble(POSITION_VOLUME);
         request.deviation = 10;
         request.magic    = InpMagicNumber;
         request.position  = ticket;
         
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
         
         StringToCharArray("BlackWolf Close", request.comment, 0, WHOLE_ARRAY, CP_UTF8);
         
         if(OrderSend(request, result))
            Print("Closed opposite position #", ticket);
         else
            Print("Failed to close #", ticket);
        }
     }
  }

//+------------------------------------------------------------------+
//| Get value from JSON string (simple parser)                          |
//+------------------------------------------------------------------+
string GetJSONValue(string json, string key)
  {
   string searchKey = "\"" + key + "\":";
   int start = StringFind(json, searchKey);
   
   if(start < 0)
     {
      searchKey = "\"" + key + "\": ";
      start = StringFind(json, searchKey);
      if(start < 0) return "";
     }
   
   start += StringLen(searchKey);
   
   while(start < StringLen(json) && StringGetCharacter(json, start) == ' ')
      start++;
   
   if(start >= StringLen(json)) return "";
   
   if(StringGetCharacter(json, start) == '"')
     {
      start++;
      int end = StringFind(json, "\"", start);
      if(end > start)
         return StringSubstr(json, start, end - start);
     }
   
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