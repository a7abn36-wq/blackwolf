//+------------------------------------------------------------------+
//|                                              BlackWolf_EA.mq5       |
//|                                    Copyright 2025, Black Wolf Trading  |
//|                                    Version 3.11 - Locale Fix           |
//+------------------------------------------------------------------+
#property copyright "Black Wolf Trading"
#property version   "3.10"
#property strict

//--- Inputs
input string   InpApiKey         = "";           // Gemini API Key
input string   InpGitHubToken    = "";           // GitHub Token (for status sync)
input double   InpLotSize        = 0.01;         // Lot Size
input int      InpMaxSpread      = 50;           // Max Spread (points)
input int      InpInterval       = 15;           // Check Every (minutes)
input int      InpCandles        = 50;           // Number of Candles
input ulong    InpMagicNumber    = 777001;       // Magic Number
input int      InpMinConfidence  = 60;           // Min Confidence %
input bool     InpDeleteOpposite = true;         // Close opposite on new signal

//--- Globals
string   API_KEY;
string   GH_TOKEN;
string   LAST_SIGNAL_ID = "";
datetime LAST_ANALYSIS_TIME = 0;
string   LAST_SIGNAL_STR  = "HOLD";
int      LAST_CONFIDENCE  = 0;
string   LAST_REASONING   = "";

// GitHub sync constants
string   GH_REPO    = "a7abn36-wq/blackwolf";
string   GH_FILE    = "ea_status.json";
string   GH_API_URL;

//+------------------------------------------------------------------+
int OnInit()
  {
   API_KEY  = InpApiKey;
   GH_TOKEN = InpGitHubToken;
   GH_API_URL = "https://api.github.com/repos/" + GH_REPO + "/contents/" + GH_FILE;
   
   if(StringLen(API_KEY) < 10)
     {
      Print("ERROR: Set your Gemini API Key in EA settings!");
      Alert("Black Wolf: Set API Key first!");
      return(INIT_PARAMETERS_INCORRECT);
     }
   
   EventSetTimer(InpInterval * 60);
   Print("Black Wolf EA v3.1 started. Symbol: ", _Symbol, " | Interval: ", InpInterval, " min");
   Comment("\n  Black Wolf EA v3.1\n  Waiting for first analysis...\n");
   
   PushStatusToGitHub();
   
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
     {
      PushStatusToGitHub();
      return;
     }
   
   if((int)(TimeCurrent() - LAST_ANALYSIS_TIME) < 60)
      return;
   
   Comment("\n  Black Wolf EA\n  Analyzing market...\n");
   
   string result = RunAnalysis();
   if(result == "")
     {
      LAST_SIGNAL_STR = "ERROR";
      Comment("\n  Black Wolf EA\n  Analysis failed. Retry next cycle...\n");
      PushStatusToGitHub();
      return;
     }
   
   ProcessSignal(result);
   PushStatusToGitHub();
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
   StringReplace(response, "```json", "");
   StringReplace(response, "```", "");
   
   int start = StringFind(response, "{\"signal");
   if(start < 0) start = StringFind(response, "{\" signal");
   if(start < 0) start = StringFind(response, "{\"signal\":");
   
   if(start < 0)
     {
      Print("No signal JSON found in response");
      return "";
     }
   
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
   
   LAST_SIGNAL_STR  = signal;
   LAST_CONFIDENCE  = conf;
   LAST_REASONING   = reason;
   
   string sigId = signal + "_" + DoubleToString(entry, 2) + "_" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES);
   
   Print("=== Black Wolf === ", signal, " | ", entry, " | SL:", sl, " | TP:", tp1, " | Conf:", conf, "%");
   Print("Reason: ", reason, " | Risk: ", risk);
   
   string c = "\n  Black Wolf EA v3.1\n";
   c += "  Signal: " + signal + " (" + IntegerToString(conf) + "%)\n";
   c += "  Entry: " + DoubleToString(entry, 2) + "\n";
   c += "  SL: " + DoubleToString(sl, 2) + "\n";
   c += "  TP1: " + DoubleToString(tp1, 2) + "\n";
   c += "  TP2: " + DoubleToString(tp2, 2) + "\n";
   c += "  GitHub Sync: ";
   if(StringLen(GH_TOKEN) >= 10)
      c += "ON";
   else
      c += "OFF (no token)";
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
//|         Force DOT decimal separator for JSON (locale fix)          |
//+------------------------------------------------------------------+
string D2S(double val, int digits)
  {
   string s = DoubleToString(val, digits);
   StringReplace(s, ",", ".");
   return s;
  }

//+------------------------------------------------------------------+
//|                    MANUAL BASE64 (no CryptEncode)                  |
//+------------------------------------------------------------------+
string Base64Encode(string data)
  {
   uchar arr[];
   int len = StringToCharArray(data, arr, 0, WHOLE_ARRAY, CP_UTF8);
   if(len > 0) len--;
   
   string b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
   string result = "";
   
   for(int i = 0; i < len; i += 3)
     {
      int b0 = (int)arr[i];
      int b1 = (i + 1 < len) ? (int)arr[i + 1] : 0;
      int b2 = (i + 2 < len) ? (int)arr[i + 2] : 0;
      
      int trip = (b0 << 16) | (b1 << 8) | b2;
      
      result += StringSubstr(b64, (trip >> 18) & 0x3F, 1);
      result += StringSubstr(b64, (trip >> 12) & 0x3F, 1);
      result += (i + 1 < len) ? StringSubstr(b64, (trip >> 6) & 0x3F, 1) : "=";
      result += (i + 2 < len) ? StringSubstr(b64, trip & 0x3F, 1) : "=";
     }
   
   return result;
  }

//+------------------------------------------------------------------+
//|                    GITHUB STATUS SYNC                              |
//+------------------------------------------------------------------+
void PushStatusToGitHub()
  {
   if(StringLen(GH_TOKEN) < 10)
      return;
   
   // 1. GET current file to obtain SHA
   string getUrl = GH_API_URL;
   string getHeaders = "Authorization: token " + GH_TOKEN + "\r\nUser-Agent: BlackWolfEA\r\n";
   
   char getResult[];
   char emptyData[];
   string getResultHeaders;
   ResetLastError();
   int res = WebRequest("GET", getUrl, getHeaders, 5000, emptyData, getResult, getResultHeaders);
   
   if(res != 200)
     {
      Print("GitHub GET failed: ", res);
      return;
     }
   
   string getResp = CharArrayToString(getResult, 0, WHOLE_ARRAY, CP_UTF8);
   string sha = GetJSONValue(getResp, "sha");
   
   if(StringLen(sha) < 10)
     {
      Print("Failed to get file SHA");
      return;
     }
   
   // 2. Build account data
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin     = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   
   int ourPositions = 0;
   double totalProfit = 0.0;
   string posDetails = "";
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      
      ourPositions++;
      double profit = PositionGetDouble(POSITION_PROFIT);
      totalProfit += profit;
      
      long posType = PositionGetInteger(POSITION_TYPE);
      string typeStr = (posType == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double posSl = PositionGetDouble(POSITION_SL);
      double posTp = PositionGetDouble(POSITION_TP);
      double vol = PositionGetDouble(POSITION_VOLUME);
      
      if(StringLen(posDetails) > 0) posDetails += ",";
      posDetails += "{\"ticket\":" + IntegerToString((long)ticket);
      posDetails += ",\"type\":\"" + typeStr + "\"";
      posDetails += ",\"volume\":" + D2S(vol, 2);
      posDetails += ",\"open_price\":" + D2S(openPrice, 2);
      posDetails += ",\"sl\":" + D2S(posSl, 2);
      posDetails += ",\"tp\":" + D2S(posTp, 2);
      posDetails += ",\"profit\":" + D2S(profit, 2);
      posDetails += "}";
     }
   
   double drawdown = 0.0;
   if(balance > 0.0)
     {
      double dd = (balance - equity) / balance * 100.0;
      if(dd > 0.0) drawdown = dd;
     }
   
   // 3. Build status JSON
   string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS);
   StringReplace(timestamp, ".", "-");
   string sJson = "{";
   sJson += "\"status\":\"online\"";
   sJson += ",\"last_update\":\"" + timestamp + "\"";
   sJson += ",\"account_balance\":" + D2S(balance, 2);
   sJson += ",\"account_equity\":" + D2S(equity, 2);
   sJson += ",\"margin\":" + D2S(margin, 2);
   sJson += ",\"free_margin\":" + D2S(freeMargin, 2);
   sJson += ",\"open_trades\":" + IntegerToString(ourPositions);
   sJson += ",\"total_profit\":" + D2S(totalProfit, 2);
   sJson += ",\"drawdown_pct\":" + D2S(drawdown, 2);
   sJson += ",\"last_signal\":\"" + LAST_SIGNAL_STR + "\"";
   sJson += ",\"last_confidence\":" + IntegerToString(LAST_CONFIDENCE);
   sJson += ",\"last_reasoning\":\"" + EscapeJSON(LAST_REASONING) + "\"";
   sJson += ",\"symbol\":\"" + _Symbol + "\"";
   sJson += ",\"open_positions\": [" + posDetails + "]";
   string lastAna = TimeToString(LAST_ANALYSIS_TIME, TIME_DATE|TIME_MINUTES);
   StringReplace(lastAna, ".", "-");
   sJson += ",\"last_analysis\":\"" + lastAna + "\"";
   sJson += "}";
   
   // 4. Base64 encode (manual - no CryptEncode needed)
   string encoded = Base64Encode(sJson);
   
   // 5. PUT to update file
   string putBody = "{\"message\":\"EA status update\",\"content\":\"" + encoded + "\",\"sha\":\"" + sha + "\"}";
   string putHeaders = "Authorization: token " + GH_TOKEN + "\r\nContent-Type: application/json\r\nUser-Agent: BlackWolfEA\r\n";
   
   char putData[];
   char putResult[];
   string putResultHeaders;
   StringToCharArray(putBody, putData, 0, WHOLE_ARRAY, CP_UTF8);
   
   ResetLastError();
   res = WebRequest("PUT", GH_API_URL, putHeaders, 5000, putData, putResult, putResultHeaders);
   
   if(res == 200 || res == 201)
     {
      Print("Status pushed to GitHub OK");
     }
   else
     {
      string errResp = CharArrayToString(putResult, 0, WHOLE_ARRAY, CP_UTF8);
      Print("GitHub PUT failed: ", res, " ", StringSubstr(errResp, 0, 300));
     }
  }

//+------------------------------------------------------------------+
//|                    JSON HELPER                                    |
//+------------------------------------------------------------------+
string GetJSONValue(string json, string key)
  {
   string searchKey = "\"" + key + "\":";
   int start = StringFind(json, searchKey);
   
   if(start < 0)
      return "";
   
   start += StringLen(searchKey);
   
   while(start < StringLen(json) && StringGetCharacter(json, start) == ' ')
      start++;
   
   if(start >= StringLen(json))
      return "";
   
   if(StringGetCharacter(json, start) == '"')
     {
      start++;
      int end = StringFind(json, "\"", start);
      if(end > start)
         return StringSubstr(json, start, end - start);
      return "";
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