//Set the delay at which sensor readings are taken in milliseconds
#define MSBETWEENREADINGS 1000

//Set how many samples you want in the moving average
#define NUMOFMOVINGAVGSAMPLES 10

//Set Current Temperature in Celsius (~25 is room temp)
#define TEMPERATURE 25

//Global Variable Initialization
volatile float startingTimeOffset;
volatile int currentBufferLocation = 0;

//Can Edit Sensor/Pin Assignments/Sensor Formatting Here. Also Initializes Buffers and Moving Average Values
//pH Sensor - Part #SEN0161 - Sensor Range 0 ~ 14 - Voltage Formatting: 5 (Arduino ADC Voltage) * 3.5 (Value Specified by Manufacturer) / 1024 (10 bit ADC)
#define PHSENSORPIN A0
#define PHSENSORFORMATVAL ((5.0*3.5)/1024) //Will be multiplied by the sample ADC value
volatile float pHMovingAvg = 0; //Stores the average value of all formatted samples
volatile float pHBuffer[NUMOFMOVINGAVGSAMPLES];
volatile float pHValue = 0; //Stores the current actual sensor value (In pH) after Moving Average Goes Through a Final Formatting Equation
//Total Dissolved Solids (TDS) Sensor - Part #SEN0244 - Sensor Range 0 ~ 1000ppm Voltage - Formatting: (5 (Arduino ADC Voltage) / 1024 (10 bit ADC)) / (1 + 0.02 * (Temperature(C) - 25))
#define TDSSENSORPIN A1
#define TDSSENSORFORMATVAL ((5.0/1024)/(1+0.02*(TEMPERATURE-25.0)))
volatile float tdsMovingAvg = 0;
volatile float tdsBuffer[NUMOFMOVINGAVGSAMPLES];
volatile float tdsValue = 0;
//Turbidity Sensor 1 - Part #TST-10 - Sensor Range 0 ~ 4000NTU - Voltage Formatting: 5 (Arduino ADC Voltage) * 1250 (Value of Slope Found from Very Rough Linear Approximation of Sensor Characteristic Curve) / 1024 (10 bit ADC)
#define TURBIDITYSENSOR1PIN A3
#define TURBIDITYSENSOR1FORMATVAL ((5.0*1250)/1024)
volatile float turbidity1MovingAvg = 0;
volatile float turbidity1Buffer[NUMOFMOVINGAVGSAMPLES];
volatile float turbidity1Value = 0; 
//Turbidity Sensor 2 - Part #TSD-10 - Sensor Range 0 ~ 4000NTU - Voltage Formatting: 5 (Arduino ADC Voltage) * 1250 (Value of Slope Found from Very Rough Linear Approximation of Sensor Characteristic Curve) / 1024 (10 bit ADC)
#define TURBIDITYSENSOR2PIN A4
#define TURBIDITYSENSOR2FORMATVAL ((5.0*1250)/1024)
volatile float turbidity2MovingAvg = 0;
volatile float turbidity2Buffer[NUMOFMOVINGAVGSAMPLES];
volatile float turbidity2Value = 0;
//Flow Rate Sensor 1 - Part #SFM3300-250-D - Sensor Range ± 250 Standard Liters/Minute (slm) - Voltage Formatting:
//Not Formatted Yet/Fully Implemented Yet
#define FLOWRATESENSOR1PIN A2
#define FLOWRATESENSOR1FORMATVAL 1
volatile float flowRate1MovingAvg = 0;
volatile float flowRate1Buffer[NUMOFMOVINGAVGSAMPLES];
volatile float flowRate1Value = 0;
//Flow Rate Sensor 2 - Adafruit Product ID #5066 - Sensor Range 1 ~ 30 Standard Liters/Minute (slm) - Voltage Formatting:
//Not Formatted/Fully Implemented Yet
#define FLOWRATESENSOR2PIN A5
#define FLOWRATESENSOR2FORMATVAL 2.25
volatile float flowRate2MovingAvg = 0;
volatile float flowRate2Buffer[NUMOFMOVINGAVGSAMPLES];
volatile float flowRate2Value = 0;

//Starts serial communication with external computer at a baud rate of 9600
//Onboard LED will blink while connecting and become solid when connected
void startSerialCommunication();

//Initializes each sensor buffer with number of readings equal to moving average sample #
//with this the starting moving average value is created
void initializeSensorBuffers();

//Reads in the current sensor value and adds it to the buffer and moving average
//while removing oldest sensor reading from buffer and moving average
void readAndPrintSensorValues();

void setup() {
  startSerialCommunication();
  initializeSensorBuffers();
  //Write header of CSV file to serial out
  Serial.println("Time-Elapsed,pH Value,TDS Value,Turbidity-1 Value,Turbidity-2 Value,Water Flow Rate-1,Water Flow Rate-2");
  //Ensures that the serial output of the time value starts at essentially 0
  startingTimeOffset = millis();
}

void loop() {
  readAndPrintSensorValues();
  delay(MSBETWEENREADINGS);
}

void startSerialCommunication(){
  //Set up serial communication at a baud rate of 9600
  Serial.begin(9600);
  //On Board LED will blink while serial communication isn't connected, and is on when established
  pinMode(LED_BUILTIN, OUTPUT);
  while(!Serial){
    digitalWrite(LED_BUILTIN, HIGH);
    delay(500);
    digitalWrite(LED_BUILTIN, LOW);
    delay(500);
  }
  digitalWrite(LED_BUILTIN, HIGH);
}

void initializeSensorBuffers(){
  for(int i = 0;i < NUMOFMOVINGAVGSAMPLES;i++){
    pHBuffer[i] = (analogRead(PHSENSORPIN)*PHSENSORFORMATVAL/NUMOFMOVINGAVGSAMPLES);
    pHMovingAvg += pHBuffer[i];
    tdsBuffer[i] = (analogRead(TDSSENSORPIN)*TDSSENSORFORMATVAL/NUMOFMOVINGAVGSAMPLES);
    tdsMovingAvg += tdsBuffer[i];
    turbidity1Buffer[i] = (analogRead(TURBIDITYSENSOR1PIN)*TURBIDITYSENSOR1FORMATVAL/NUMOFMOVINGAVGSAMPLES);
    turbidity1MovingAvg += turbidity1Buffer[i];
    turbidity2Buffer[i] = (analogRead(TURBIDITYSENSOR2PIN)*TURBIDITYSENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES);
    turbidity2MovingAvg += turbidity2Buffer[i];
    flowRate1Buffer[i] = (analogRead(FLOWRATESENSOR1PIN)*FLOWRATESENSOR1FORMATVAL/NUMOFMOVINGAVGSAMPLES);
    flowRate1MovingAvg += flowRate1Buffer[i];

    flowRate2Buffer[i] = (analogRead(FLOWRATESENSOR2PIN)*FLOWRATESENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES);
    // while(!digitalRead(FLOWRATESENSOR2PIN));
    // while(digitalRead(FLOWRATESENSOR2PIN));
    // int flowRate2TimeOn1 = millis();
    // while(!digitalRead(FLOWRATESENSOR2PIN));
    // while(digitalRead(FLOWRATESENSOR2PIN));
    // int flowRate2TimeOn2 = millis();
    // float fR2PulsesPerSecond = 1/(flowRate2TimeOn2 - flowRate2TimeOn1);
    // flowRate2Buffer[currentBufferLocation] = fR2PulsesPerSecond*FLOWRATESENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES; //2.25 milliliters per pulse

    flowRate2MovingAvg += flowRate2Buffer[i];
  }
}

void readAndPrintSensorValues(){
  //Prints out time in seconds since program started running
  Serial.print((millis()-startingTimeOffset)/1000);
  Serial.print(",");
  //pH Sensor
  pHMovingAvg -= pHBuffer[currentBufferLocation]; //Removes value of the oldest data in buffer from the moving average
  pHBuffer[currentBufferLocation] = (analogRead(PHSENSORPIN)*PHSENSORFORMATVAL/NUMOFMOVINGAVGSAMPLES); //Reads in analog sensor data to buffer and formats according to sensor specification
  pHMovingAvg += pHBuffer[currentBufferLocation]; //Adds sensor value to the moving average
  pHValue = pHMovingAvg; //pH value already calculated but done for consistency between the sensors
  Serial.print(pHValue); //Prints out value
  Serial.print(","); //Adds a comma to end for CSV formatting
  //TDS Sensor
  tdsMovingAvg -= tdsBuffer[currentBufferLocation];
  tdsBuffer[currentBufferLocation] = (analogRead(TDSSENSORPIN)*TDSSENSORFORMATVAL/NUMOFMOVINGAVGSAMPLES);
  tdsMovingAvg += tdsBuffer[currentBufferLocation];
  tdsValue = (133.42*tdsMovingAvg*tdsMovingAvg*tdsMovingAvg - 255.86*tdsMovingAvg*tdsMovingAvg + 857.39*tdsMovingAvg)*0.5; //Equation to convert voltage to tds value
  Serial.print(tdsValue);
  Serial.print(",");
  //Turbidity Sensor 1
  turbidity1MovingAvg -= turbidity1Buffer[currentBufferLocation];
  turbidity1Buffer[currentBufferLocation] = (analogRead(TURBIDITYSENSOR1PIN)*TURBIDITYSENSOR1FORMATVAL/NUMOFMOVINGAVGSAMPLES);
  turbidity1MovingAvg += turbidity1Buffer[currentBufferLocation];
  turbidity1Value = 5000.0-turbidity1MovingAvg; //Very Rough Linear Approximation of Sensor Characteristic Curve, Haven't Found Official Values Yet
  Serial.print(turbidity1Value);
  Serial.print(",");
  //Turbidity Sensor 2
  turbidity2MovingAvg -= turbidity2Buffer[currentBufferLocation];
  turbidity2Buffer[currentBufferLocation] = (analogRead(TURBIDITYSENSOR2PIN)*TURBIDITYSENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES);
  turbidity2MovingAvg += turbidity2Buffer[currentBufferLocation];
  turbidity2Value = 5000.0-turbidity2MovingAvg; //Very Rough Linear Approximation of Sensor Characteristic Curve, Haven't Found Official Values Yet
  Serial.print(turbidity2Value);
  Serial.print(",");
  //Flow Rate Sensor 1
  flowRate1MovingAvg -= flowRate1Buffer[currentBufferLocation];
  flowRate1Buffer[currentBufferLocation] = (analogRead(FLOWRATESENSOR1PIN)*FLOWRATESENSOR1FORMATVAL/NUMOFMOVINGAVGSAMPLES);
  flowRate1MovingAvg += flowRate1Buffer[currentBufferLocation];
  flowRate1Value = flowRate1MovingAvg;
  Serial.print(flowRate1Value);
  Serial.print(",");
  //Flow Rate Sensor 2
  flowRate2MovingAvg -= flowRate2Buffer[currentBufferLocation];

  flowRate2Buffer[currentBufferLocation] = (analogRead(FLOWRATESENSOR2PIN)*FLOWRATESENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES);

  // while(!digitalRead(FLOWRATESENSOR2PIN));
  // while(digitalRead(FLOWRATESENSOR2PIN));
  // int flowRate2TimeOn1 = millis();
  // while(!digitalRead(FLOWRATESENSOR2PIN));
  // while(digitalRead(FLOWRATESENSOR2PIN));
  // int flowRate2TimeOn2 = millis();
  // float fR2PulsesPerSecond = 1/(flowRate2TimeOn2 - flowRate2TimeOn1);
  // flowRate2Buffer[currentBufferLocation] = fR2PulsesPerSecond*FLOWRATESENSOR2FORMATVAL/NUMOFMOVINGAVGSAMPLES; //2.25 milliliters per pulse

  flowRate2MovingAvg += flowRate2Buffer[currentBufferLocation];
  flowRate2Value = flowRate2MovingAvg;
  Serial.println(flowRate2Value); //Prints final sensor value and moves to a new line

  //Adjust buffer location variable
  if(currentBufferLocation == (NUMOFMOVINGAVGSAMPLES - 1)){
    currentBufferLocation = 0;
  }
  else{
    currentBufferLocation++;
  }
}

