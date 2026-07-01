# Multi-stage build for the .NET 9 API.
# Build context must be the `backend/` directory (the API references Core + Infrastructure).
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore AIQuality.API/AIQuality.API.csproj
RUN dotnet publish AIQuality.API/AIQuality.API.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet", "AIQuality.API.dll"]
