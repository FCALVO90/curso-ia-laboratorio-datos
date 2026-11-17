#!/usr/bin/env Rscript
# -*- coding: UTF-8 -*-
# SOLUCION UNICA R1-R8 - NYC YELLOW TAXI 2024

options(stringsAsFactors = FALSE, scipen = 999)
Sys.setlocale("LC_NUMERIC", "C")

suppressPackageStartupMessages({
  library(arrow)
  library(data.table)
  library(ggplot2)
})

HOME <- path.expand("~")
PROYECTO <- file.path(HOME, "curso_ia")
DATA_DIR <- file.path(PROYECTO, "datos", "raw", "taxi")
LOOKUP <- file.path(DATA_DIR, "taxi_zone_lookup.csv")
SALIDAS_DIR <- file.path(PROYECTO, "salidas", "taxi", "r")
CSV_DIR <- file.path(SALIDAS_DIR, "csv")
GRAFICOS_DIR <- file.path(SALIDAS_DIR, "graficos")
JSON_DIR <- file.path(SALIDAS_DIR, "json")

dir.create(CSV_DIR, recursive=TRUE, showWarnings=FALSE)
dir.create(GRAFICOS_DIR, recursive=TRUE, showWarnings=FALSE)
dir.create(JSON_DIR, recursive=TRUE, showWarnings=FALSE)

args <- commandArgs(trailingOnly=TRUE)
valor_arg <- function(nombre, defecto=NULL) {
  i <- match(nombre, args)
  if (!is.na(i) && i < length(args)) args[i+1] else defecto
}
mes <- valor_arg("--mes", "01")
solo_txt <- valor_arg("--solo", paste0("R", 1:8, collapse=","))
solo <- trimws(strsplit(solo_txt, ",")[[1]])
n_muestra <- as.integer(valor_arg("--muestra-modelo", "100000"))

separador <- function(t) cat("\n", paste(rep("=",78),collapse=""), "\n ", t, "\n", paste(rep("=",78),collapse=""), "\n", sep="")
guardar_csv <- function(x, nombre) {
  ruta <- file.path(CSV_DIR, nombre); fwrite(as.data.table(x), ruta)
  cat("[OK] CSV guardado:", ruta, "\n")
}
guardar_fig <- function(p, nombre, w=14, h=9) {
  ruta <- file.path(GRAFICOS_DIR, nombre); ggsave(ruta, p, width=w, height=h, dpi=200)
  cat("[OK] Figura guardada:", ruta, "\n")
}
fmt <- function(x) format(x, big.mark=".", decimal.mark=",", scientific=FALSE, trim=TRUE)

cargar_mes <- function(mes) {
  ruta <- file.path(DATA_DIR, sprintf("yellow_tripdata_2024-%s.parquet", mes))
  if (!file.exists(ruta)) stop("No existe: ", ruta)
  t0 <- proc.time()[3]; d <- as.data.table(read_parquet(ruta))
  cat(sprintf("[OK] %s: %s filas en %.2f s\n", basename(ruta), fmt(nrow(d)), proc.time()[3]-t0))
  d
}

preparar_variables <- function(df) {
  d <- copy(df)
  d[, tpep_pickup_datetime := as.POSIXct(tpep_pickup_datetime)]
  d[, tpep_dropoff_datetime := as.POSIXct(tpep_dropoff_datetime)]
  d[, duracion_min := as.numeric(difftime(tpep_dropoff_datetime, tpep_pickup_datetime, units="mins"))]
  d[, velocidad_mph := fifelse(duracion_min > 0, trip_distance/(duracion_min/60), NA_real_)]
  d[, `:=`(fecha=as.Date(tpep_pickup_datetime), hora=as.integer(format(tpep_pickup_datetime, "%H")))]
  d[, dia_semana_num := as.POSIXlt(tpep_pickup_datetime)$wday]
  dias <- c("Domingo","Lunes","Martes","Miercoles","Jueves","Viernes","Sabado")
  d[, dia_semana := dias[dia_semana_num+1]]
  d[, fin_semana := dia_semana_num %in% c(0,6)]
  d
}

filtrar_validos <- function(d, mes) {
  ini <- as.POSIXct(sprintf("2024-%s-01", mes), tz="UTC")
  fin <- seq(ini, by="month", length.out=2)[2]
  d[tpep_pickup_datetime >= ini & tpep_pickup_datetime < fin &
    tpep_dropoff_datetime > tpep_pickup_datetime & duracion_min > 0 & duracion_min <= 1440 &
    trip_distance > 0 & fare_amount > 0 & total_amount > 0]
}

R1 <- function(df, mes) {
  separador("R1 - DESCARGAR, LEER Y MIRAR EL DATO")
  cat("Dimensiones:", fmt(nrow(df)), "filas x", ncol(df), "columnas\n")
  print(sapply(df, class)); cat("Memoria:", round(as.numeric(object.size(df))/1024^2,2), "MB\n")
  resumen <- df[, .(viajes=.N, distancia_media=mean(trip_distance,na.rm=TRUE), importe_medio=mean(total_amount,na.rm=TRUE)), by=payment_type]
  print(resumen); guardar_csv(resumen, sprintf("R1_resumen_pago_2024-%s.csv",mes))
  ruta <- file.path(DATA_DIR,sprintf("yellow_tripdata_2024-%s.parquet",mes))
  cols <- c("tpep_pickup_datetime","trip_distance","payment_type","tip_amount","total_amount")
  t0 <- proc.time()[3]; parcial <- as.data.table(read_parquet(ruta,col_select=all_of(cols)))
  cat(sprintf("[EXTRA] Lectura de 5 columnas: %.2f s; memoria %.2f MB\n",proc.time()[3]-t0,as.numeric(object.size(parcial))/1024^2))
}

R2 <- function(df, mes) {
  separador("R2 - CALIDAD DEL DATO CON R")
  d <- preparar_variables(df)
  calidad <- data.table(columna=names(d), nulos=sapply(d,function(x)sum(is.na(x))))
  calidad[, porcentaje := 100*nulos/nrow(d)][order(-nulos)]
  print(calidad[nulos>0]); guardar_csv(calidad,sprintf("R2_calidad_2024-%s.csv",mes))
  anom <- data.table(regla=c("pasajeros_0_o_na","distancia_no_positiva","tarifa_no_positiva","importe_no_positivo","duracion_no_positiva","duracion_mayor_24h"), casos=c(sum(is.na(d$passenger_count)|d$passenger_count==0),sum(d$trip_distance<=0,na.rm=TRUE),sum(d$fare_amount<=0,na.rm=TRUE),sum(d$total_amount<=0,na.rm=TRUE),sum(d$duracion_min<=0,na.rm=TRUE),sum(d$duracion_min>1440,na.rm=TRUE)))
  print(anom); guardar_csv(anom,sprintf("R2_anomalias_2024-%s.csv",mes))
  v <- filtrar_validos(d,mes); cat("Viajes validos:",fmt(nrow(v)),"; descartados:",fmt(nrow(d)-nrow(v)),"\n"); v
}

R3 <- function(v,mes) {
  separador("R3 - VISUALIZACION CON GGPLOT2")
  set.seed(42); m <- v[sample(.N,min(150000,.N))]
  m <- m[trip_distance<=quantile(v$trip_distance,.995,na.rm=TRUE)&total_amount<=quantile(v$total_amount,.99,na.rm=TRUE)]
  p1 <- ggplot(m,aes(trip_distance))+geom_histogram(bins=60,fill="#D9491A")+scale_y_log10()+labs(title="Distancia de viaje",x="Millas",y="Frecuencia log")
  p2 <- ggplot(m,aes(factor(payment_type),total_amount))+geom_boxplot(outlier.shape=NA)+labs(title="Importe por tipo de pago",x="Tipo de pago",y="Importe total ($)")
  p3 <- ggplot(m,aes(trip_distance,fare_amount))+geom_bin_2d(bins=60)+scale_fill_viridis_c(trans="log10")+labs(title="Distancia frente a tarifa")
  if(requireNamespace("patchwork",quietly=TRUE)) guardar_fig(p1+p2+p3+patchwork::plot_layout(ncol=2),sprintf("R3_panel_exploratorio_2024-%s.png",mes)) else {guardar_fig(p1,sprintf("R3_distancia_2024-%s.png",mes));guardar_fig(p2,sprintf("R3_pago_2024-%s.png",mes));guardar_fig(p3,sprintf("R3_distancia_tarifa_2024-%s.png",mes))}
}

R4 <- function(v,mes) {
  separador("R4 - SERIES TEMPORALES")
  hora <- v[,.(viajes=.N),by=.(fecha_hora=as.POSIXct(cut(tpep_pickup_datetime,"hour")))][order(fecha_hora)]
  hora[,media24:=frollmean(viajes,24,align="right",fill=NA)]
  dia <- v[,.(viajes=.N),by=.(fecha=as.Date(tpep_pickup_datetime))][order(fecha)]
  perfil <- v[,.(viajes=.N),by=.(tipo_dia=ifelse(fin_semana,"Fin de semana","Laborable"),hora)]
  p1<-ggplot(hora,aes(fecha_hora,viajes))+geom_line(alpha=.4)+geom_line(aes(y=media24),linewidth=1)+labs(title="Demanda horaria")
  p2<-ggplot(dia,aes(fecha,viajes))+geom_line()+geom_point()+labs(title="Viajes diarios")
  p3<-ggplot(perfil,aes(hora,viajes,color=tipo_dia))+geom_line()+geom_point()+labs(title="Perfil horario")
  if(requireNamespace("patchwork",quietly=TRUE)) guardar_fig(p1/p2/p3,sprintf("R4_series_temporales_2024-%s.png",mes),14,12)
  guardar_csv(dia,sprintf("R4_viajes_diarios_2024-%s.csv",mes))
}

enriquecer_zonas <- function(v) {
  z<-fread(LOOKUP); pu<-copy(z); setnames(pu,c("LocationID","Borough","Zone","service_zone"),c("PULocationID","borough_origen","zona_origen","service_origen")); do<-copy(z); setnames(do,c("LocationID","Borough","Zone","service_zone"),c("DOLocationID","borough_destino","zona_destino","service_destino")); merge(merge(v,pu,by="PULocationID",all.x=TRUE),do,by="DOLocationID",all.x=TRUE)
}

R5 <- function(v,mes) {
  separador("R5 - CRUCE CON ZONAS")
  vz<-enriquecer_zonas(v)
  rutas<-vz[,.(viajes=.N,importe_medio=mean(total_amount,na.rm=TRUE)),by=.(borough_origen,zona_origen,borough_destino,zona_destino)][order(-viajes)][1:15]
  matriz<-dcast(vz,borough_origen~borough_destino,fun.aggregate=length,value.var="total_amount",fill=0)
  print(rutas); guardar_csv(rutas,sprintf("R5_top_rutas_2024-%s.csv",mes)); guardar_csv(matriz,sprintf("R5_matriz_boroughs_2024-%s.csv",mes))
  top<-vz[,.(viajes=.N),by=zona_origen][order(-viajes)][1:15]
  p<-ggplot(top,aes(reorder(zona_origen,viajes),viajes))+geom_col(fill="#D9491A")+coord_flip()+labs(title="Zonas con mas recogidas",x=NULL)
  guardar_fig(p,sprintf("R5_zonas_2024-%s.png",mes))
  cat(sprintf("[EXTRA] Misma zona: %.2f%%\n",100*mean(vz$PULocationID==vz$DOLocationID,na.rm=TRUE))); vz
}

R6 <- function(vz,mes) {
  separador("R6 - MAPAS CON SF")
  shp<-list.files(DATA_DIR,"\\.shp$",recursive=TRUE,full.names=TRUE)[1]
  if(is.na(shp)){cat("[AVISO] No se encontro shapefile.\n");return()}
  if(!requireNamespace("sf",quietly=TRUE)){cat("[AVISO] Falta sf.\n");return()}
  zonas<-sf::st_read(shp,quiet=TRUE); id<-intersect(c("LocationID","location_i","OBJECTID"),names(zonas))[1]
  agg<-vz[,.(viajes=.N,propina_media=mean(tip_amount,na.rm=TRUE),tarifa_media=mean(fare_amount,na.rm=TRUE)),by=PULocationID];agg[,tip_pct:=100*propina_media/tarifa_media]
  mapa<-merge(zonas,agg,by.x=id,by.y="PULocationID",all.x=TRUE)
  p<-ggplot(mapa)+geom_sf(aes(fill=viajes),color=NA)+scale_fill_viridis_c()+theme_void()+labs(title="Viajes por zona")
  guardar_fig(p,sprintf("R6_mapa_viajes_2024-%s.png",mes))
}

R7 <- function(vz,mes,n) {
  separador("R7 - MODELO DE PROPINAS")
  if(!requireNamespace("ranger",quietly=TRUE)){cat("[AVISO] Instala ranger para R7.\n");return()}
  d<-vz[payment_type==1&fare_amount>0];d[,tip_pct:=100*tip_amount/fare_amount];d<-d[tip_pct>=0&tip_pct<=100];d[,aeropuerto:=grepl("Airport",zona_origen,ignore.case=TRUE)];d<-d[complete.cases(d[,.(hora,trip_distance,duracion_min,passenger_count,fare_amount,fin_semana,borough_origen,aeropuerto,tip_pct)])]
  set.seed(42);d<-d[sample(.N,min(n,.N))];idx<-sample(seq_len(nrow(d)),floor(.8*nrow(d)));train<-d[idx];test<-d[-idx]
  f<-tip_pct~hora+trip_distance+duracion_min+passenger_count+fare_amount+fin_semana+borough_origen+aeropuerto
  lm1<-lm(f,train);pr1<-predict(lm1,test);rf<-ranger::ranger(f,data=train,num.trees=180,importance="permutation");pr2<-predict(rf,test)$predictions
  met<-data.table(modelo=c("Regresion lineal","Ranger"),test_rmse=c(sqrt(mean((test$tip_pct-pr1)^2)),sqrt(mean((test$tip_pct-pr2)^2))),test_r2=c(1-sum((test$tip_pct-pr1)^2)/sum((test$tip_pct-mean(test$tip_pct))^2),1-sum((test$tip_pct-pr2)^2)/sum((test$tip_pct-mean(test$tip_pct))^2)))
  print(met);guardar_csv(met,sprintf("R7_metricas_2024-%s.csv",mes)); imp<-data.table(variable=names(rf$variable.importance),importancia=as.numeric(rf$variable.importance));guardar_csv(imp,sprintf("R7_importancia_2024-%s.csv",mes))
}

R8 <- function() {
  separador("R8 - GRAN VOLUMEN Y PANEL ANUAL")
  archivos<-sort(list.files(DATA_DIR,"yellow_tripdata_2024-.*\\.parquet$",full.names=TRUE));res<-list()
  for(ruta in archivos){m<-substr(tools::file_path_sans_ext(basename(ruta)),nchar(tools::file_path_sans_ext(basename(ruta)))-1,nchar(tools::file_path_sans_ext(basename(ruta))));d<-as.data.table(read_parquet(ruta,col_select=c(tpep_pickup_datetime,tpep_dropoff_datetime,trip_distance,tip_amount,total_amount,fare_amount)));d[,dur_h:=as.numeric(difftime(tpep_dropoff_datetime,tpep_pickup_datetime,units="hours"))];x<-d[dur_h>0&dur_h<=24&trip_distance>0&fare_amount>0&total_amount>0];vel<-x$trip_distance/x$dur_h;vel<-vel[vel>=0&vel<=100];res[[length(res)+1]]<-data.table(mes=m,viajes=nrow(x),propina_media=mean(x$tip_amount,na.rm=TRUE),velocidad_media_mph=mean(vel,na.rm=TRUE),importe_medio=mean(x$total_amount,na.rm=TRUE));cat("[OK] Mes",m,"procesado\n");rm(d,x);gc()}
  anual<-rbindlist(res);med<-median(anual$viajes);mad0<-median(abs(anual$viajes-med));anual[,z_robusto_viajes:=if(mad0==0)0 else .6745*(viajes-med)/mad0];anual[,mes_atipico:=abs(z_robusto_viajes)>3.5];guardar_csv(anual,"R8_resumen_anual_2024.csv")
  largo<-melt(anual,id.vars="mes",measure.vars=c("viajes","propina_media","velocidad_media_mph","importe_medio"));p<-ggplot(largo,aes(mes,value,group=1))+geom_line(color="#D9491A")+geom_point(color="#D9491A")+facet_wrap(~variable,scales="free_y",ncol=2)+labs(title="Panel anual 2024",x="Mes",y=NULL);guardar_fig(p,"R8_panel_anual_2024.png",15,10)
  hall<-list(mes_mas_viajes=anual$mes[which.max(anual$viajes)],mes_mayor_propina_media=anual$mes[which.max(anual$propina_media)],mes_mayor_velocidad_media=anual$mes[which.max(anual$velocidad_media_mph)],meses_atipicos=anual[mes_atipico == TRUE, mes]);if(requireNamespace("jsonlite",quietly=TRUE))jsonlite::write_json(hall,file.path(JSON_DIR,"R8_hallazgos.json"),pretty=TRUE,auto_unbox=TRUE)
  print(anual)
}

separador("INICIO - SOLUCION EJERCICIOS R NYC TAXI")
cat("Datos:",DATA_DIR,"\nCSV:",CSV_DIR,"\nGraficos:",GRAFICOS_DIR,"\nJSON:",JSON_DIR,"\nEjercicios:",paste(solo,collapse=", "),"\n")
if(!dir.exists(DATA_DIR))stop("No existe ",DATA_DIR)
necesita_mes<-any(solo %in% paste0("R",1:7));df<-if(necesita_mes)cargar_mes(mes) else NULL;validos<-NULL;vz<-NULL
if("R1"%in%solo)R1(df,mes)
if(any(solo%in%paste0("R",2:7)))validos<-R2(df,mes)
if("R3"%in%solo)R3(validos,mes)
if("R4"%in%solo)R4(validos,mes)
if(any(solo%in%paste0("R",5:7)))vz<-R5(validos,mes)
if("R6"%in%solo)R6(vz,mes)
if("R7"%in%solo)R7(vz,mes,max(5000,n_muestra))
if("R8"%in%solo)R8()
separador("FIN - EJERCICIOS R FINALIZADOS")
cat("CSV:",CSV_DIR,"\nGraficos:",GRAFICOS_DIR,"\nJSON:",JSON_DIR,"\n")
