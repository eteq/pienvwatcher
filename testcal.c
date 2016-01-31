#include <stdio.h>

typedef long signed int BME280_S32_t;
typedef long unsigned int BME280_U32_t;
typedef long long signed int BME280_S64_t;

int dig_P6 = -7 ;
int dig_P9 = 4285 ;
int dig_H3 = 0 ;
int dig_P7 = 9900 ;
int dig_P5 = -10 ;
int dig_P1 = 37298 ;
int dig_H2 = 357 ;
int dig_P2 = -10829 ;
int dig_H4 = 322 ;
int dig_P8 = -10230 ;
int dig_H6 = 30 ;
int dig_T1 = 28224 ;
int dig_H1 = 75 ;
int dig_P3 = 3024 ;
int dig_P4 = 11341 ;
int dig_H5 = 0 ;
int dig_T3 = 50 ;
int dig_T2 = 26110 ;


// Returns temperature in DegC, resolution is 0.01 DegC. Output value of “5123” equals 51.23 DegC.
// t_fine carries fine temperature as global value
BME280_S32_t t_fine;
BME280_S32_t BME280_compensate_T_int32(BME280_S32_t adc_T)
{
BME280_S32_t var1, var2, T;
var1 = ((((adc_T>>3) - ((BME280_S32_t)dig_T1<<1))) * ((BME280_S32_t)dig_T2)) >> 11;
var2 = (((((adc_T>>4) - ((BME280_S32_t)dig_T1)) * ((adc_T>>4) - ((BME280_S32_t)dig_T1))) >> 12) *
((BME280_S32_t)dig_T3)) >> 14;
t_fine = var1 + var2;
T = (t_fine * 5 + 128) >> 8;
return T;
}



// Returns pressure in Pa as unsigned 32 bit integer in Q24.8 format (24 integer bits and 8 fractional bits).
// Output value of “24674867” represents 24674867/256 = 96386.2 Pa = 963.862 hPa
BME280_U32_t BME280_compensate_P_int64(BME280_S32_t adc_P)
{
BME280_S64_t var1, var2, p;
var1 = ((BME280_S64_t)t_fine) - 128000;
var2 = var1 * var1 * (BME280_S64_t)dig_P6;
var2 = var2 + ((var1*(BME280_S64_t)dig_P5)<<17);
var2 = var2 + (((BME280_S64_t)dig_P4)<<35);
var1 = ((var1 * var1 * (BME280_S64_t)dig_P3)>>8) + ((var1 * (BME280_S64_t)dig_P2)<<12);
var1 = (((((BME280_S64_t)1)<<47)+var1))*((BME280_S64_t)dig_P1)>>33;
if (var1 == 0)
{
return 0; // avoid exception caused by division by zero
}
p = 1048576-adc_P;
p = (((p<<31)-var2)*3125)/var1;
var1 = (((BME280_S64_t)dig_P9) * (p>>13) * (p>>13)) >> 25;
var2 = (((BME280_S64_t)dig_P8) * p) >> 19;
p = ((p + var1 + var2) >> 8) + (((BME280_S64_t)dig_P7)<<4);
return (BME280_U32_t)p;
}



// Returns humidity in %RH as unsigned 32 bit integer in Q22.10 format (22 integer and 10 fractional bits).
// Output value of “47445” represents 47445/1024 = 46.333 %RH
BME280_U32_t bme280_compensate_H_int32(BME280_S32_t adc_H)
{
BME280_S32_t v_x1_u32r;
v_x1_u32r = (t_fine - ((BME280_S32_t)76800));
v_x1_u32r = (((((adc_H << 14) - (((BME280_S32_t)dig_H4) << 20) - (((BME280_S32_t)dig_H5) * v_x1_u32r)) +
((BME280_S32_t)16384)) >> 15) * (((((((v_x1_u32r * ((BME280_S32_t)dig_H6)) >> 10) * (((v_x1_u32r *
((BME280_S32_t)dig_H3)) >> 11) + ((BME280_S32_t)32768))) >> 10) + ((BME280_S32_t)2097152)) *
((BME280_S32_t)dig_H2) + 8192) >> 14));
v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((BME280_S32_t)dig_H1)) >> 4));
v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
return (BME280_U32_t)(v_x1_u32r>>12);
}

// time,pressure,temperature,humidity
// 2016-01-29_02:56:47,274239,527824,29244

int main(int argc, char * argv[])
{
   //code
	BME280_S32_t temp = BME280_compensate_T_int32(522496);
	BME280_U32_t pres = BME280_compensate_P_int64(265035);
	BME280_U32_t hum = bme280_compensate_H_int32(28299);
	printf("temp=%f", temp/100.);
	printf(" pressure=%f", pres/256000.);
	printf(" humidity=%f\n", hum/1024.);
}